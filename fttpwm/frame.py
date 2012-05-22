"""FTTPWM: Window frame class

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from argparse import Namespace
import logging

import xcb
from xcb.xproto import Atom, CW, ConfigWindow, EventMask, PropMode, WindowClass
from xcb.xproto import ButtonPressEvent, EnterNotifyEvent, LeaveNotifyEvent, KeyPressEvent
from xcb.xproto import ExposeEvent, ConfigureNotifyEvent, MapNotifyEvent, UnmapNotifyEvent

import xpybutil
import xpybutil.event
import xpybutil.ewmh as ewmh
import xpybutil.icccm as icccm
from xpybutil.util import get_atom as atom
import xpybutil.mousebind as mousebind

import cairo

from .bind import FilteredHandler
from .ewmh import EWMHAction, EWMHWindowState
from .mouse import bindMouse, raiseAndMoveWindow
from .settings import settings
from .themes import Theme, State, Region
from .themes import fonts as fonts
from .themes.gradients import linearGradient, Direction
from .utils import convertAttributes


logger = logging.getLogger("test-cairo")

UINT32_MAX = 2 ** 32

settings.setDefaults(
        theme=Theme(
            focused=State(
                titlebar=Region(
                    font=("drift", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL),
                    font_size=5,
                    text=(0, 0, 0),
                    background=linearGradient(Direction.Vertical, (1, 0.9, 0, 1), (1, 0.3, 0, 1)),
                    height=16,
                    opacity=1,
                    ),
                border=Region(
                    width=1,
                    ),
                ),
            unfocused=State(
                titlebar=Region(
                    font=("drift", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL),
                    font_size=5,
                    text=(0, 0, 0),
                    background=linearGradient(Direction.Vertical, (1, 0.7, 0.3, 0.8), (1, 0.5, 0.3, 0.8)),
                    height=16,
                    opacity=0.7,
                    ),
                border=Region(
                    width=1,
                    ),
                ),
            )
        )

# Default font options
fonts.options.set(
        antialias=fonts.antialias.default,
        hintMetrics=fonts.hintMetrics.on,
        hintStyle=fonts.hintStyle.slight,
        subpixelOrder=fonts.subpixelOrder.default,
        )


class WindowFrame(object):
    """A Cairo-backed titlebar and window frame.

    """
    def __init__(self, wm, clientWindowID):
        self.wm = wm
        self.frameWindowID = xpybutil.conn.generate_id()
        self.clientWindowID = clientWindowID
        self.focused = False

        self.windowAttributes = {
                CW.OverrideRedirect: 1,
                CW.BackPixel: wm.unfocusedBorderColor,
                }

        # Start fetching some information about the client window.
        cookies = Namespace()
        cookies.geometry = xpybutil.conn.core.GetGeometry(clientWindowID)
        cookies.ewmhTitle = ewmh.get_wm_name(clientWindowID)
        cookies.icccmTitle = icccm.get_wm_name(clientWindowID)
        xpybutil.conn.flush()

        self.logger = logging.getLogger("fttpwm.frame.WindowFrame.{}".format(self.frameWindowID))

        #TODO: Keep these updated where appropriate!
        ewmh.set_wm_state(clientWindowID, [EWMHWindowState.MaximizedVert])
        ewmh.set_wm_allowed_actions(clientWindowID, [
                EWMHAction.Move,
                EWMHAction.Resize,
                #EWMHAction.Minimize,
                #EWMHAction.Shade,
                #EWMHAction.Stick,
                #EWMHAction.MaximizeHorz,
                #EWMHAction.MaximizeVert,
                #EWMHAction.Fullscreen,
                #EWMHAction.ChangeDesktop,
                EWMHAction.Close,
                ])

        #TODO: Implement _NET_WM_PING!
        #if atom('_NET_WM_PING') in icccm.get_wm_protocols(clientWindow).reply():
        #    self.startPing()

        leftFrame = rightFrame = bottomFrame = self.theme.border.width
        topFrame = self.theme.titlebar.height
        ewmh.set_frame_extents(clientWindowID, leftFrame, rightFrame, topFrame, bottomFrame)

        # Get window geometry.
        geom = cookies.geometry.reply()
        del cookies.geometry
        self.x, self.y, self.width, self.height = geom.x, geom.y, geom.width, geom.height

        # Create frame window.
        self.frameWindowID, cookies.createWindow = wm.createWindow(
                self.x, self.y, self.width, self.height,
                attributes=self.windowAttributes, windowID=self.frameWindowID, checked=True
                )

        # Set window title.
        self.title = cookies.ewmhTitle.reply() or cookies.icccmTitle.reply()
        del cookies.ewmhTitle
        del cookies.icccmTitle

        cookies.setTitle = ewmh.set_wm_name_checked(self.frameWindowID, self.title)

        # Reparent client window to frame.
        xpybutil.conn.core.ReparentWindow(clientWindowID, self.frameWindowID, leftFrame, topFrame)

        # Set up Cairo.
        self.surface = cairo.XCBSurface(xpybutil.conn, self.frameWindowID, wm.visual, self.width, self.height)
        self.context = cairo.Context(self.surface)

        self.subscribeToEvents()
        self.activateBindings()

        # Show window.
        cookies.showWindow = xpybutil.conn.core.MapWindowChecked(self.frameWindowID)

        # Flush the connection, and make sure all of our requests succeeded.
        xpybutil.conn.flush()
        for name, cookie in cookies._get_kwargs():
            try:
                cookie.check()
            except:
                self.logger.exception("Error while checking results of %s query!", name)

    def subscribeToEvents(self):
        xpybutil.window.listen(self.frameWindowID, 'ButtonPress', 'EnterWindow', 'Exposure', 'PropertyChange',
                'StructureNotify', 'SubstructureNotify')
        xpybutil.event.connect('ConfigureNotify', self.frameWindowID, self.onConfigureNotify)
        xpybutil.event.connect('EnterNotify', self.frameWindowID, self.onEnterNotify)
        xpybutil.event.connect('Expose', self.frameWindowID, self.onExpose)
        xpybutil.event.connect('MapNotify', self.frameWindowID, self.onMapNotify)
        xpybutil.event.connect('UnmapNotify', self.frameWindowID, self.onUnmapNotify)
        xpybutil.event.connect('DestroyNotify', self.frameWindowID, self.onDestroyNotify)

    def activateBindings(self):
        xcb.xproto.ButtonMask._1
        bindMouse({
                '1': raiseAndMoveWindow,
                })

    def onConfigureNotify(self, event):
        if (self.width, self.height) != (event.width, event.height):
            # Window size changed; resize surface and redraw.
            self.logger.debug("Window size changed to {}.".format((event.width, event.height)))
            self.surface.set_size(event.width, event.height)
            self.width, self.height = event.width, event.height
            attributes = convertAttributes({
                    ConfigWindow.Width: self.innerWidth,
                    ConfigWindow.Height: self.innerHeight,
                    })
            xpybutil.conn.core.ConfigureWindow(self.clientWindowID, *attributes)
            self.paint()

    def onEnterNotify(self, event):
        pass

    def onExpose(self, event):
        self.paint()

    def onMapNotify(self, event):
        self.paint()

    def onUnmapNotify(self, event):
        pass

    def onDestroyNotify(self, event):
        pass

    def onGainedFocus(self):
        self.focused = True
        self.wm_states.append(atom('_NET_WM_STATE_FOCUSED'))
        ewmh.set_wm_state(self.clientWindow, self.wm_states)

        xpybutil.conn.core.ChangeWindowAttributesChecked(self.frameWindowID, *convertAttributes({
                CW.BackPixel: self.wm.focusedBorderColor,
                })).check()

        self.applyTheme()

    def onLostFocus(self):
        self.focused = False
        self.wm_states.remove(atom('_NET_WM_STATE_FOCUSED'))
        ewmh.set_wm_state(self.clientWindow, self.wm_states)

        xpybutil.conn.core.ChangeWindowAttributesChecked(self.frameWindowID, *convertAttributes({
                CW.BackPixel: self.wm.unfocusedBorderColor,
                })).check()

        self.applyTheme()

    def applyTheme(self):
        ewmh.set_wm_window_opacity(self.frameWindowID, self.theme.opacity)

    @property
    def innerWidth(self):
        return self.width - 2 * self.theme.border.width

    @property
    def innerHeight(self):
        return self.height - self.theme.border.width - self.theme.titlebar.height

    @property
    def theme(self):
        if self.focused:
            return settings.theme.focused
        else:
            return settings.theme.unfocused

    def paint(self):
        self.context.set_operator(cairo.OPERATOR_OVER)

        titlebarPattern = self.theme.titlebar.background
        titlebarPattern.set_matrix(cairo.Matrix(
                xx=1.0 / self.width,
                yy=1.0 / self.theme.titlebar.height
                ))
        self.context.set_source(titlebarPattern)
        self.context.paint()

        self.context.set_source_rgb(*self.theme.titlebar.text)
        self.context.select_font_face(*self.theme.titlebar.font)
        self.context.set_font_options(fonts.options.fontOptions)

        userFontEmSize, _ = self.context.device_to_user_distance(self.theme.titlebar.font_size, 0)
        self.context.set_font_size(userFontEmSize)

        xBearing, yBearing, textWidth, textHeight = self.context.text_extents(self.title)[:4]
        self.context.move_to(
                0.5 * self.width - textWidth / 2 - xBearing,
                0.5 * self.theme.titlebar.height - textHeight / 2 - yBearing
                )
        self.context.show_text(self.title)

        self.surface.flush()
        xpybutil.conn.flush()
