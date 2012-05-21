"""FTTPWM: Window frame class

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import logging

import xcb
from xcb.xproto import Atom, CW, EventMask, PropMode, WindowClass
from xcb.xproto import ButtonPressEvent, EnterNotifyEvent, LeaveNotifyEvent, KeyPressEvent
from xcb.xproto import ExposeEvent, ConfigureNotifyEvent, MapNotifyEvent, UnmapNotifyEvent

import xpybutil
import xpybutil.event as event
import xpybutil.mousebind as mousebind

import cairo

from .bind import FilteredHandler
from .mouse import bindMouse, raiseAndMoveWindow


logger = logging.getLogger("test-cairo")


class WindowFrame(object):
    """A Cairo-backed titlebar and window frame.

    """
    def __init__(self, app, title):
        self.app = app
        self.title = title

        self.windowID = self.app.conn.generate_id()
        self.logger = logging.getLogger("test-cairo.WindowFrame.{}".format(self.windowID))
        self.app._windowCreated(self)

        x, y = 0, 0
        width, height = 640, 480
        self.width, self.height = width, height

        cookies = []

        # Create titlebar window.
        winAttribs = {
                #CW.OverrideRedirect: 1,
                CW.BackPixel: self.app.black,
                CW.EventMask: EventMask.KeyPress | EventMask.ButtonPress
                    | EventMask.EnterWindow | EventMask.LeaveWindow | EventMask.Exposure
                    | EventMask.StructureNotify  # gives us ConfigureNotify events
                }

        self.windowID, cookie = self.app.createWindow(
                x, y, width, height,
                attributes=winAttribs, windowID=self.windowID, checked=True
                )
        cookies.append(cookie)

        # Set window title.
        cookies.append(self.app.core.ChangePropertyChecked(
            PropMode.Replace, self.windowID, Atom.WM_NAME, Atom.STRING, 8, len(title), title
            ))

        # Set up Cairo.
        self.surface = cairo.XCBSurface(self.app.conn, self.windowID, self.app.visual, width, height)
        self.context = cairo.Context(self.surface)

        self.fontOptions = cairo.FontOptions()
        self.fontOptions.set_hint_metrics(cairo.HINT_METRICS_ON)

        self.subscribeToEvents()
        self.activateBindings()

        # Show window.
        cookies.append(self.app.core.MapWindowChecked(self.windowID))

        # Flush the connection, and make sure all of our requests succeeded.
        self.app.flush()
        for cookie in cookies:
            cookie.check()

    def subscribeToEvents(self):
        event.connect('ConfigureNotify', self.windowID, self.onConfigureNotify)
        event.connect('Expose', self.windowID, self.onExpose)
        event.connect('MapNotify', self.windowID, self.onMapNotify)
        event.connect('UnmapNotify', self.windowID, self.onUnmapNotify)
        event.connect('EnterNotify', self.windowID, self.onEnterNotify)
        event.connect('LeaveNotify', self.windowID, self.onLeaveNotify)

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
            self.paint()

    def onExpose(self, event):
        self.paint()

    def onMapNotify(self, event):
        self.paint()

    def onUnmapNotify(self, event):
        pass

    def onEnterNotify(self, event):
        pass

    def onLeaveNotify(self, event):
        pass

    def paint(self):
        self.logger.debug("Drawing...")
        self.context.set_operator(cairo.OPERATOR_OVER)

        linear = cairo.LinearGradient(0, 0, 0, self.height)
        linear.add_color_stop_rgba(0.00, 1, 0.9, 0, 1)
        linear.add_color_stop_rgba(1.00, 1, 0.3, 0, 1)
        self.context.set_source(linear)
        self.context.paint()

        self.context.set_source_rgb(0.0, 0.0, 0.0)
        self.context.select_font_face("drift", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        self.context.set_font_options(self.fontOptions)

        userFontEmSize, _ = self.context.device_to_user_distance(5, 0)
        self.context.set_font_size(userFontEmSize)

        x_bearing, y_bearing, width, height = self.context.text_extents(self.title)[:4]
        self.context.move_to(
                0.5 * self.width - width / 2 - x_bearing,
                0.5 * self.height - height / 2 - y_bearing)
        self.context.show_text(self.title)

        self.surface.flush()
        self.app.flush()
