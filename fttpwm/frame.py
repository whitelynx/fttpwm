"""FTTPWM: Window frame class

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from argparse import Namespace
import logging

import xcb
from xcb.xproto import CW, ConfigWindow, StackMode

import xpybutil
import xpybutil.event
import xpybutil.ewmh as ewmh
import xpybutil.icccm as icccm
from xpybutil.util import get_atom as atom
import xpybutil.mousebind as mousebind

import cairo

from .bind import FilteredHandler
from .ewmh import EWMHAction, EWMHWindowState
from .icccm import ICCCMWindowState
from .mouse import bindMouse, raiseAndMoveWindow
from .settings import settings
from .themes import Default, fonts
from .utils import convertAttributes


UINT32_MAX = 2 ** 32

settings.setDefaults(
        theme=Default()
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
        self.visible = False  # Whether or not this window is currently visible on the screen
        self.viewable = False  # Whether or not this window would be visible if its workspace were shown

        self._workspace = None

        self.windowAttributes = {
                CW.OverrideRedirect: 1,
                CW.BackPixel: wm.black,
                }

        # Start fetching some information about the client window.
        cookies = Namespace()
        cookies.geometry = xpybutil.conn.core.GetGeometry(clientWindowID)
        cookies.ewmhTitle = ewmh.get_wm_name(clientWindowID)
        cookies.icccmTitle = icccm.get_wm_name(clientWindowID)
        cookies.icccmProtocols = icccm.get_wm_protocols(clientWindowID)
        xpybutil.conn.flush()

        self.logger = logging.getLogger(
                "fttpwm.frame.WindowFrame.{}(client:{})".format(
                    self.frameWindowID,
                    self.clientWindowID
                    ))

        icccm.set_wm_state(clientWindowID, ICCCMWindowState.Normal, xcb.NONE)

        #TODO: Keep these updated where appropriate!
        self.wm_states = [EWMHWindowState.MaximizedVert]
        ewmh.set_wm_state(clientWindowID, self.wm_states)
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
        #if atom('_NET_WM_PING') in icccm.get_wm_protocols(clientWindowID).reply():
        #    self.startPing()

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

        # Set the frame's _NET_WM_NAME to match the client's title.
        cookies.setTitle = ewmh.set_wm_name_checked(self.frameWindowID, self.title)

        # Reparent client window to frame.
        clientX, clientY = settings.theme.getClientGeometry(self)[:2]
        xpybutil.conn.core.ReparentWindow(clientWindowID, self.frameWindowID, clientX, clientY)

        # Set up Cairo.
        self.surface = cairo.XCBSurface(xpybutil.conn, self.frameWindowID, wm.visual, self.width, self.height)
        self.context = cairo.Context(self.surface)

        self.applyTheme()
        self.subscribeToEvents()
        self.activateBindings()

        # Get ICCCM _NET_WM_PROTOCOLS property.
        self.protocols = cookies.icccmProtocols.reply()
        del cookies.icccmProtocols

        # Flush the connection, and make sure all of our requests succeeded.
        xpybutil.conn.flush()
        for name, cookie in cookies._get_kwargs():
            try:
                cookie.check()
            except:
                self.logger.exception("Error while checking results of %s query!", name)

    def __repr__(self):
        return "<Frame {} for client {}>".format(self.frameWindowID, self.clientWindowID)

    def subscribeToEvents(self):
        self.logger.info("Subscribing to events.")

        # Frame window events
        xpybutil.event.connect('ConfigureNotify', self.frameWindowID, self.onConfigureNotify)
        xpybutil.event.connect('EnterNotify', self.frameWindowID, self.onEnterNotify)
        xpybutil.event.connect('Expose', self.frameWindowID, self.onExpose)
        xpybutil.event.connect('MapNotify', self.frameWindowID, self.onMapNotify)

        xpybutil.window.listen(self.frameWindowID, 'ButtonPress', 'EnterWindow', 'Exposure', 'PropertyChange',
                'StructureNotify', 'SubstructureNotify')

        # Client window events
        xpybutil.event.connect('UnmapNotify', self.clientWindowID, self.onClientUnmapNotify)
        xpybutil.event.connect('DestroyNotify', self.clientWindowID, self.onClientDestroyNotify)

        xpybutil.window.listen(self.clientWindowID, 'ButtonPress', 'EnterWindow', 'Exposure', 'PropertyChange')

    def unsubscribeFromEvents(self):
        self.logger.info("Unsubscribing from events.")

        # Client window events
        if self.clientWindowID is not None:
            try:
                xpybutil.window.listen(self.clientWindowID)
            except:
                self.logger.exception("Error while clearing listened events on client window %r!", self.clientWindowID)

            xpybutil.event.disconnect('UnmapNotify', self.clientWindowID)
            xpybutil.event.disconnect('DestroyNotify', self.clientWindowID)

        # Frame window events
        if self.frameWindowID is not None:
            try:
                xpybutil.window.listen(self.frameWindowID)
            except:
                self.logger.exception("Error while clearing listened events on frame window %r!", self.frameWindowID)

            xpybutil.event.disconnect('ConfigureNotify', self.frameWindowID)
            xpybutil.event.disconnect('EnterNotify', self.frameWindowID)
            xpybutil.event.disconnect('Expose', self.frameWindowID)
            xpybutil.event.disconnect('MapNotify', self.frameWindowID)

    def activateBindings(self):
        xcb.xproto.ButtonMask._1
        bindMouse({
                '1': raiseAndMoveWindow,
                })

    ## Commands ####
    def hide(self):
        self.logger.debug("hide: Hiding %r.", self)
        try:
            xpybutil.conn.core.UnmapWindowChecked(self.frameWindowID).check()
        except:
            self.logger.exception("hide: Error unmapping %r!", self)
        else:
            self.viewable = False
            self.addWMState(EWMHWindowState.Hidden)

    def show(self):
        self.logger.debug("show: Showing %r.", self)
        try:
            xpybutil.conn.core.MapWindowChecked(self.frameWindowID).check()
        except:
            self.logger.exception("show: Error mapping %r!", self)
        else:
            self.viewable = True
            self.removeWMState(EWMHWindowState.Hidden)

    def moveResize(self, x, y, width, height, flush=True):
        attributes = convertAttributes({
                ConfigWindow.X: x,
                ConfigWindow.Y: y,
                ConfigWindow.Width: width,
                ConfigWindow.Height: height,
                ConfigWindow.StackMode: StackMode.Above
                })
        xpybutil.conn.core.ConfigureWindow(self.frameWindowID, *attributes)

        if flush:
            xpybutil.conn.flush()

    ## X events ####
    def onConfigureNotify(self, event):
        if (self.width, self.height) != (event.width, event.height):
            # Window size changed; resize surface and redraw.
            self.logger.debug("onConfigureNotify: Window size changed to %r.", (event.width, event.height))
            self.surface.set_size(event.width, event.height)
            self.width, self.height = event.width, event.height
            attributes = convertAttributes({
                    ConfigWindow.Width: self.innerWidth,
                    ConfigWindow.Height: self.innerHeight,
                    })
            xpybutil.conn.core.ConfigureWindow(self.clientWindowID, *attributes)
            self.paint()

    def onEnterNotify(self, event):
        self.logger.debug("onEnterNotify: %r", event.__dict__)
        if not self.focused:
            self.wm.focusWindow(self)

    def onExpose(self, event):
        # A count of 0 denotes the last Expose event in a series of contiguous Expose events; this check lets us
        # collapse such series into a single call to paint() so we don't get extraneous redraws.
        if event.count == 0:
            self.paint()

    def onMapNotify(self, event):
        self.visible = True
        self.viewable = True
        self.paint()

    def onUnmapNotify(self, event):
        self.visible = False

    def onClientUnmapNotify(self, event):
        self.logger.debug("onClientUnmapNotify: %r", event.__dict__)

        if self.frameWindowID is None:
            self.logger.warn("onClientUnmapNotify: No frame window to hide! PANIC!")
            return

        try:
            self.hide()
        except:
            self.logger.exception("Error hiding frame window!")

    def onClientDestroyNotify(self, event):
        self.logger.debug("onClientDestroyNotify: %r", event.__dict__)

        if self.clientWindowID is not None:
            try:
                self.wm.unmanageWindow(self)
            except:
                self.logger.exception("onClientDestroyNotify: Error unmanaging client window %r!", self.clientWindowID)

            self.clientWindowID = None

        self.unsubscribeFromEvents()

        if self.frameWindowID is not None:
            #TODO: Do we want to clear and save unused frames in a pool so we don't need to destroy and re-create them?
            try:
                xpybutil.conn.core.DestroyWindowChecked(self.frameWindowID).check()
            except:
                self.logger.exception("onClientDestroyNotify: Error destroying frame window %r!", self.frameWindowID)

            self.frameWindowID = None

    ## Window State ####
    def addWMState(self, state):
        self.wm_states.append(state)
        if self.clientWindowID is not None:
            ewmh.set_wm_state(self.clientWindowID, self.wm_states)

    def removeWMState(self, state):
        self.wm_states.remove(state)
        if self.clientWindowID is not None:
            ewmh.set_wm_state(self.clientWindowID, self.wm_states)

    ## WM events ####
    def onGainedFocus(self):
        self.logger.debug("onGainedFocus")
        self.focused = True
        self.addWMState(EWMHWindowState.Focused)

        if self.frameWindowID is not None:
            self.applyTheme()

    def onLostFocus(self):
        self.logger.debug("onLostFocus")
        self.focused = False
        self.removeWMState(EWMHWindowState.Focused)

        if self.frameWindowID is not None:
            self.applyTheme()

    def onWorkspaceVisibilityChanged(self):
        if self.clientWindowID is None:
            self.logger.warn("onWorkspaceVisibilityChanged: No client window! PANIC!")
            return

        if self.frameWindowID is None:
            self.logger.warn("onWorkspaceVisibilityChanged: No frame window! PANIC!")
            return

        if self.workspace.visible:
            # If this window is viewable, map it.
            if self.viewable:
                self.logger.debug("onWorkspaceVisibilityChanged: Showing %r.", self)
                try:
                    xpybutil.conn.core.MapWindowChecked(self.frameWindowID).check()
                except:
                    self.logger.exception("onWorkspaceVisibilityChanged: Error mapping %r!", self)

                icccm.set_wm_state(self.clientWindowID, ICCCMWindowState.Normal, xcb.NONE)

        else:
            # If this window is currently visible, unmap it.
            if self.visible:
                self.logger.debug("onWorkspaceVisibilityChanged: Hiding %r.", self)
                try:
                    xpybutil.conn.core.UnmapWindowChecked(self.frameWindowID).check()
                except:
                    self.logger.exception("onWorkspaceVisibilityChanged: Error unmapping %r!", self)

                icccm.set_wm_state(self.clientWindowID, ICCCMWindowState.Iconic, xcb.NONE)

    ## Properties ####
    @property
    def innerWidth(self):
        return self.innerGeometry[2]

    @property
    def innerHeight(self):
        return self.innerGeometry[3]

    @property
    def innerGeometry(self):
        return settings.theme.getClientGeometry(self)

    @property
    def workspace(self):
        return self._workspace

    @workspace.setter
    def workspace(self, workspace):
        if self._workspace is not None:
            self._workspace.visibilityChanged.disconnect(self.onWorkspaceVisibilityChanged)

        self._workspace = workspace

        self.onWorkspaceVisibilityChanged()
        workspace.visibilityChanged.connect(self.onWorkspaceVisibilityChanged)

    ## Visual Stuff ####
    def applyTheme(self):
        settings.theme.apply(self)
        self.paint()

    def paint(self):
        self.context.set_operator(cairo.OPERATOR_OVER)

        settings.theme.paintWindow(self.context, self)

        self.surface.flush()
        xpybutil.conn.flush()
