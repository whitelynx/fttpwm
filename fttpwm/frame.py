"""FTTPWM: Window frame class

Copyright (c) 2012-2013 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from argparse import Namespace
from collections import defaultdict
import json
import logging
import time

import xcb
from xcb.xproto import Atom, CW, ConfigWindow, ConfigureNotifyEvent, PropMode, StackMode

import xpybutil
import xpybutil.event
import xpybutil.ewmh as ewmh
import xpybutil.icccm as icccm
from xpybutil.util import get_atom as atom

import cairo

from .ewmh import EWMHAction, EWMHWindowState
from .signals import Signal
from .signaled import SignaledSet, SignaledDict
from .settings import settings
from .themes import Default, fonts
from .utils.x import convertAttributes
from . import singletons


UINT32_MAX = 2 ** 32

settings.setDefaults(
        theme=Default(),
        focusOnMouseEnter=False,
        focusOnMouseClick=True,
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
    #FIXME: This class is huge and monolithic. It'd be nice if we could refactor it to separate the Frame logic from
    # the Client logic; this would allow us to effectively manage frameless windows, as well as to reuse the Frame
    # for panes in static tiling.

    #TODO: Implement "shaded" mode; also, use this to display tabs/titlebars for hidden windows in layouts like
    # TabbedLayout and StackedLayout.

    def __init__(self, clientWindowID):
        self.frameWindowID = xcb.NONE
        self.clientWindowID = clientWindowID

        self.logger = logging.getLogger(
                "fttpwm.frame.WindowFrame.{}(client:{})".format(
                    self.frameWindowID,
                    self.clientWindowID
                    ))

        self.requestShow = Signal()
        self.closed = Signal()

        self.surface = None
        self.context = None

        self.clientMapped = False  # Whether or not the client window is currently mapped on the screen
        self.frameMapped = False  # Whether or not the frame window is currently mapped on the screen
        self.clientDestroyed = False  # Whether or not the client window has been destroyed
        self.viewable = False  # Whether or not this window would be visible if its workspace were shown
        self.initialized = False  # Whether or not this frame has finished initializing

        self._workspace = None
        self._icccmState = icccm.State.Withdrawn
        self._icccmIconWindowID = xcb.NONE
        self.addedToWorkspace = None  # When this frame was added to its workspace

        self.ewmhStates = SignaledSet()
        self.ewmhStates.updated.connect(self._updateEWMHState)

        self.layoutInfo = SignaledDict()
        self.layoutInfo.updated.connect(self._updateLayoutInfo)

        self.subscribeToClientEvents()

    def __repr__(self):
        return "<Frame {} for client {}>".format(self.frameWindowID, self.clientWindowID)

    def subscribeToClientEvents(self):
        self.logger.info("Subscribing to client window events.")

        xpybutil.event.connect('MapNotify', self.clientWindowID, self.onClientMapNotify)
        xpybutil.event.connect('UnmapNotify', self.clientWindowID, self.onClientUnmapNotify)
        xpybutil.event.connect('DestroyNotify', self.clientWindowID, self.onClientDestroyNotify)
        #TODO: Listen for all property changes on the client window so we can respond to changes? Actually, this should
        # probably be handling for ClientMessage requests sent to the root instead.

        xpybutil.window.listen(self.clientWindowID, 'PropertyChange', 'StructureNotify')

    def subscribeToFrameEvents(self):
        self.logger.info("Subscribing to frame window events.")

        xpybutil.event.connect('ConfigureNotify', self.frameWindowID, self.onConfigureNotify)
        xpybutil.event.connect('EnterNotify', self.frameWindowID, self.onEnterNotify)
        xpybutil.event.connect('Expose', self.frameWindowID, self.onExpose)
        xpybutil.event.connect('MapNotify', self.frameWindowID, self.onMapNotify)
        xpybutil.event.connect('UnmapNotify', self.frameWindowID, self.onUnmapNotify)

        xpybutil.window.listen(self.frameWindowID, 'ButtonPress', 'EnterWindow', 'Exposure', 'PropertyChange',
                'StructureNotify', 'SubstructureNotify')

    def unsubscribeFromEvents(self):
        self.logger.info("Unsubscribing from events.")

        # Client window events
        if self.clientWindowID is not None:
            if not self.clientDestroyed:
                try:
                    xpybutil.window.listen(self.clientWindowID)
                except:
                    self.logger.exception("Error while clearing listened events on client window %r!",
                            self.clientWindowID)

            xpybutil.event.disconnect('MapNotify', self.clientWindowID)
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
            xpybutil.event.disconnect('UnmapNotify', self.frameWindowID)

    def activateBindings(self):
        #FIXME: What is this for, and do we still need it?
        pass
        #bindMouse({
        #        #'1': FloatingBindings.raiseAndMoveWindow,
        #        }, context=self.frameWindowID)

    ## Commands ####
    def minimize(self):
        self.logger.debug("minimize: Marking %r as hidden.", self)
        self.viewable = False

        if self.initialized:
            self.ewmhStates.add(EWMHWindowState.Hidden)
            self.hide()

    def restore(self):
        self.logger.debug("restore: Marking %r as not hidden.", self)
        self.viewable = True

        if self.initialized:
            self.ewmhStates.discard(EWMHWindowState.Hidden)
            self.show()

    def hide(self):
        """Hide this window. (both the frame and the client)

        This does not set the EWMH state; to do that, use `minimize`. (which then calls this method) To quote the EWMH
        spec:

            The second option [for implementing virtual desktops] is to keep all managed windows as children of the
            root window and unmap the frames of those which are not on the current desktop. Unmapped windows should be
            placed in IconicState, according to the ICCCM. Windows which are actually iconified or minimized should
            have the _NET_WM_STATE_HIDDEN property set, to communicate to pagers that the window should not be
            represented as "onscreen."

        """
        self.logger.trace("hide: Hiding %r.", self)

        self.icccmState = icccm.State.Iconic
        #FIXME: EWMH state!

        if self.clientMapped:
            self.logger.debug("hide: Unmapping client window.")
            xpybutil.conn.core.UnmapWindow(self.clientWindowID)

        if self.frameMapped:
            self.logger.debug("hide: Unmapping frame window.")
            xpybutil.conn.core.UnmapWindow(self.frameWindowID)

        xpybutil.conn.flush()

    def show(self):
        """Request that this window be shown.

        """
        self.logger.debug("show: Requesting show for %r.", self)
        self.requestShow(self)

    def _doShow(self):
        """Show this frame window.

        Most code should NOT call this; instead call `show`. This will map the client and frame windows, regardless of
        whether or not we're on the correct workspace.

        This should ONLY be called by the following code:

        - the current workspace's layout, when it's arranging its windows (see `ListLayout.onFramePositioned`,
          `FloatingLayout.arrange`, etc.)
        - `self.onClientMapRequest` ...though this is debatable, and may well be incorrect.

        """
        self.logger.trace("_doShow: Showing %r.", self)

        # If this window is viewable, map it.
        if self.viewable:
            cookies = list()

            if not self.clientMapped:
                self.logger.debug("_doShow: Mapping client window.")
                cookies.append(xpybutil.conn.core.MapWindowChecked(self.clientWindowID))

            if not self.frameMapped:
                self.logger.debug("_doShow: Mapping frame window.")
                cookies.append(xpybutil.conn.core.MapWindowChecked(self.frameWindowID))

            for cookie in cookies:
                try:
                    cookie.check()
                except:
                    self.logger.exception("_doShow: Error mapping %r or its client!", self)

            self.icccmState = icccm.State.Normal
            #FIXME: EWMH state!

        else:
            self.logger.warn("_doShow called, but frame is not viewable!")

    def moveResize(self, x, y, width, height, flush=True):
        if (self.x, self.y, self.width, self.height) == (x, y, width, height):
            self.logger.trace("moveResize: Geometry didn't change; skipping ConfigureWindow call.")

        attributes = convertAttributes({
                ConfigWindow.X: x,
                ConfigWindow.Y: y,
                ConfigWindow.Width: width,
                ConfigWindow.Height: height,
                })
        xpybutil.conn.core.ConfigureWindow(self.frameWindowID, *attributes)

        if flush:
            xpybutil.conn.flush()

    def focus(self, flush=True):
        """Focus this window.

        If this window is not on the current workspace, this will most likely fail somehow. To switch to a window's
        workspace and then focus that window, call `frame.activate()` instead.

        """
        if not self.focused:
            singletons.wm.focusWindow(self)

        if flush:
            xpybutil.conn.flush()

    def activate(self, flush=True):
        """Raise and focus this window, switching to its workspace first if needed.

        """
        if self.workspace != singletons.wm.workspaces.current:
            singletons.wm.workspaces.current = self.workspace

        self.raise_(False)
        self.focus(flush)

    def raise_(self, flush=True):
        xpybutil.conn.core.ConfigureWindow(self.frameWindowID, *convertAttributes({
                ConfigWindow.StackMode: StackMode.Above
                }))

        if flush:
            xpybutil.conn.flush()

    def lower(self, flush=True):
        xpybutil.conn.core.ConfigureWindow(self.frameWindowID, *convertAttributes({
                ConfigWindow.StackMode: StackMode.Below
                }))

        if flush:
            xpybutil.conn.flush()

    def setProperty(self, property, data, type=Atom.STRING, format=8, mode=PropMode.Replace, data_len=None):
        singletons.x.setProperty(self.frameWindowID, property, data, type, format, mode, data_len)

    def setClientProperty(self, property, data, type=Atom.STRING, format=8, mode=PropMode.Replace, data_len=None):
        singletons.x.setProperty(self.clientWindowID, property, data, type, format, mode, data_len)

    def getLayoutInfo(self, layout):
        layoutType = layout.layoutInfoKey
        return self.layoutInfo.get(layoutType, {})

    def setLayoutInfo(self, layout, data):
        layoutType = layout.layoutInfoKey
        self.layoutInfo[layoutType] = data

    ## Frame events ####
    def onConfigureNotify(self, event):
        # If this isn't a ConfigureNotify for our frame, ignore it.
        if event.window != self.frameWindowID:
            return

        # If there's any other ConfigureNotify events for this window in the queue, ignore this one.
        xpybutil.event.read(block=False)
        for ev in xpybutil.event.peek():
            if isinstance(ev, ConfigureNotifyEvent) and ev.event == ev.window and ev.event == self.frameWindowID:
                self.logger.debug("onConfigureNotify: Ignoring event; more are in the queue.")
                return

        self.x, self.y = event.x, event.y
        self.width, self.height = event.width, event.height

        self.logger.debug("onConfigureNotify: Window geometry changed to %rx%r+%r+%r",
                self.width, self.height, self.x, self.y)

        # Window size changed; resize surface and reset clip region.
        self.surface.set_size(event.width, event.height)
        self.context.reset_clip()

        # Send client window a ConfigureNotify as well (regardless of whether the client's geometry actually changed)
        # so windows can update if their absolute coordinates changed.
        clientX, clientY, clientW, clientH = self.innerGeometry

        attributes = convertAttributes({
                ConfigWindow.X: clientX,
                ConfigWindow.Y: clientY,
                ConfigWindow.Width: clientW,
                ConfigWindow.Height: clientH,
                })
        xpybutil.conn.core.ConfigureWindow(self.clientWindowID, *attributes)

        singletons.eventloop.callWhenIdle(self.paint)

    def onEnterNotify(self, event):
        self.logger.trace("onEnterNotify: %r", event.__dict__)

        if settings.focusOnMouseEnter:
            self.focus

    def onExpose(self, event):
        singletons.eventloop.callWhenIdle(self.paint)

    def onMapNotify(self, event):
        self.frameMapped = True

        singletons.eventloop.callWhenIdle(self.paint)

    def onUnmapNotify(self, event):
        self.frameMapped = False

    ## Client events ####

    ## Client window states
    #     Event     |     From      | Initial WM_STATE | WM_HINTS.initial_state |     WM Actions        | New WM_STATE
    #               |               |                  |                        | Client Window | Frame |
    #------------------------------------------------------------------------------------------------------------------
    # MapNotify     | client window | Withdrawn        | Iconic                 | Unmap         | Unmap | Iconic
    #  "            |  "            |  "               | Normal                 | Map (?)       | Map   | Normal
    #  "            |  "            | Iconic           | -                      |  "            |  "    |  "
    # ClientMessage |  "            | Normal           | -                      | Unmap         | Unmap | Iconic
    # UnmapNotify   |  "            | Iconic           | -                      | Unmap (?)     | Unmap | Withdrawn
    #  "            |  "            | Normal           | -                      |  "            |  "    |  "

    def onClientMapRequest(self):
        self.logger.debug("onClientMapRequest: Initial ICCCM state: %r", self.icccmState)

        if self.icccmState == icccm.State.Iconic:
            # If the window is mapping itself after being in the Iconic state, we should show the frame too.
            self._doShow()
            return

        elif self.icccmState != icccm.State.Withdrawn:
            # The window isn't transitioning from Withdrawn to another state, so ignore its hints. (it should be
            # sending a client request if it wants to change them after initially mapping the window)
            return

        # The rest of this method should ONLY be called if this is an initial MapNotify. (if the window was previously
        # in the Withdrawn state)
        self.logger.debug("onClientMapRequest: Client window initial map notification received; setting up frame.")

        # Start fetching some information about the client window.
        cookies = Namespace()
        cookies.geometry = xpybutil.conn.core.GetGeometry(self.clientWindowID)
        cookies.ewmhTitle = ewmh.get_wm_name(self.clientWindowID)
        cookies.icccmTitle = icccm.get_wm_name(self.clientWindowID)
        cookies.icccmProtocols = icccm.get_wm_protocols(self.clientWindowID)
        cookies.icccmClientHints = icccm.get_wm_hints(self.clientWindowID)
        xpybutil.conn.flush()

        if self.frameWindowID == xcb.NONE:
            self.frameWindowID = xpybutil.conn.generate_id()
            self.frameWindowAttributes = {
                    CW.OverrideRedirect: 1,
                    CW.BackPixel: singletons.x.black,
                    }

            newLoggerName = "fttpwm.frame.WindowFrame.{}(client:{})".format(
                    self.frameWindowID,
                    self.clientWindowID
                    )
            self.logger.debug("Creating frame window; logger renaming to %r.", newLoggerName)
            self.logger = logging.getLogger(newLoggerName)

            # Get window geometry.
            geom = cookies.geometry.reply()
            del cookies.geometry
            self.x, self.y, self.width, self.height = geom.x, geom.y, geom.width, geom.height

            # Create the frame window.
            self.frameWindowID, cookies.createWindow = singletons.x.createWindow(
                    self.x, self.y, self.width, self.height,
                    attributes=self.frameWindowAttributes, windowID=self.frameWindowID, checked=True
                    )

            # Set up Cairo.
            self.surface = cairo.XCBSurface(xpybutil.conn, self.frameWindowID, singletons.x.visual,
                    self.width, self.height)
            self.context = cairo.Context(self.surface)

            self.activateBindings()

        else:
            # Get window geometry.
            geom = cookies.geometry.reply()
            del cookies.geometry

            # Move and resize the frame window.
            self.moveResize(geom.x, geom.y, geom.width, geom.height, flush=False)

        # Set window title.
        self.title = cookies.ewmhTitle.reply() or cookies.icccmTitle.reply()
        self.logger.info("New window has title %r", self.title)
        del cookies.ewmhTitle
        del cookies.icccmTitle

        # Set the frame's _NET_WM_NAME to match the client's title.
        cookies.setTitle = ewmh.set_wm_name_checked(self.frameWindowID, self.title)

        # Reparent client window to frame.
        clientX, clientY = settings.theme.getClientGeometry(self)[:2]
        xpybutil.conn.core.ReparentWindow(self.clientWindowID, self.frameWindowID, clientX, clientY)

        #TODO: Keep these updated where appropriate!
        self.ewmhStates.clear()
        ewmh.set_wm_allowed_actions(self.clientWindowID, [
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

        self.icccmClientHints = cookies.icccmClientHints.reply()
        del cookies.icccmClientHints

        icccmFlags = defaultdict(bool)
        if self.icccmClientHints is not None and 'flags' in self.icccmClientHints:
            icccmFlags = self.icccmClientHints['flags']

        #icccm.get_wm_hints => {
        #    'flags': {
        #        'Input': v[0] & Hint.Input > 0,
        #        'State': v[0] & Hint.State > 0,
        #        'IconPixmap': v[0] & Hint.IconPixmap > 0,
        #        'IconWindow': v[0] & Hint.IconWindow > 0,
        #        'IconPosition': v[0] & Hint.IconPosition > 0,
        #        'IconMask': v[0] & Hint.IconMask > 0,
        #        'WindowGroup': v[0] & Hint.WindowGroup > 0,
        #        'Message': v[0] & Hint.Message > 0,
        #        'Urgency': v[0] & Hint.Urgency > 0
        #    },
        #    'input': v[1],
        #    'initial_state': v[2],
        #    'icon_pixmap': v[3],
        #    'icon_window': v[4],
        #    'icon_x': v[5],
        #    'icon_y': v[6],
        #    'icon_mask': v[7],
        #    'window_group': v[8],
        #}
        #TODO: Respect more of the above hints!

        #TODO: Honor the initial value of _NET_WM_STATE! (ewmh.get_wm_state)
        #TODO: Honor the initial value of _NET_WM_DESKTOP! (ewmh.get_wm_desktop)

        # Default to showing the window normally.
        initialState = icccm.State.Normal

        if icccmFlags['State']:
            initialState = self.icccmClientHints['initial_state']

        if initialState == icccm.State.Iconic:
            # The window wants to be minimized initially.
            self.icccmState = icccm.State.Iconic
            self.ewmhStates.add(EWMHWindowState.Hidden)
            self.hide()

        else:
            if initialState != icccm.State.Normal:
                self.logger.warn("Unrecognized WM_HINTS.initial_state value: %r", initialState)

            # The window wants to be shown initially.
            self.icccmState = icccm.State.Normal
            self.ewmhStates.discard(EWMHWindowState.Hidden)
            self.show()

        # If there's an icon window, hide it; we don't use it.
        if icccmFlags['IconWindow']:
            self.icccmIconWindowID = self.icccmClientHints['icon_window']
            self.logger.debug("Client specified an icon window (WM_HINTS.icon_window=%r); unmapping it.",
                    self.icccmIconWindowID)

            xpybutil.conn.core.UnmapWindow(self.icccmIconWindowID)

        else:
            self.icccmIconWindowID = xcb.NONE

        self.applyTheme()
        self.subscribeToFrameEvents()

        # Get ICCCM _NET_WM_PROTOCOLS property.
        self.protocols = cookies.icccmProtocols.reply()
        del cookies.icccmProtocols

        #TODO: Implement _NET_WM_PING!
        #if atom('_NET_WM_PING') in self.protocols:
        #    self.startPing()

        self.initialized = True

        # Flush the connection, and make sure all of our requests succeeded.
        xpybutil.conn.flush()
        for name, cookie in cookies._get_kwargs():
            try:
                cookie.check()
            except:
                self.logger.exception("Error while checking results of %s query!", name)

        singletons.wm.workspaces.placeOnWorkspace(self)

    def onClientMapNotify(self, event):
        self.logger.debug("onClientMapNotify: %r (ICCCM state: %r)", event.__dict__, self.icccmState)

        self.clientMapped = True

        if self.viewable:
            self.ewmhStates.discard(EWMHWindowState.Hidden)
            self.show()

        else:
            self.logger.warn("onClientMapNotify: We are not viewable! Hiding.")
            self.ewmhStates.add(EWMHWindowState.Hidden)
            self.hide()

    def onClientUnmapNotify(self, event):
        """Handle UnmapNotify events for the client window.

        If the client window was withdrawn, we remove the _NET_WM_STATE and _NET_WM_DESKTOP properties.

        From the EWMH spec sections on _NET_WM_STATE and _NET_WM_DESKTOP (the language is identical for both):

            The Window Manager should remove the property whenever a window is withdrawn but it should leave the
            property in place when it is shutting down, e.g. in response to losing ownership of the WM_Sn manager
            selection.

        """
        self.logger.debug("onClientUnmapNotify: %r", event.__dict__)
        #TODO: Only do most of this stuff if the window wasn't unmapped because of switching workspaces!

        self.clientMapped = False

        if self.icccmState == icccm.State.Withdrawn:
            # Remove the window's _NET_WM_STATE and _NET_WM_DESKTOP properties.
            xpybutil.conn.core.DeleteProperty(self.clientWindowID, atom('_NET_WM_STATE'))
            xpybutil.conn.core.DeleteProperty(self.clientWindowID, atom('_NET_WM_DESKTOP'))

            self.onClosed()

        if self.frameWindowID is None:
            self.logger.warn("onClientUnmapNotify: No frame window to hide! PANIC!")
            return

        try:
            self.hide()
        except:
            self.logger.exception("Error hiding frame window!")

    def onClientDestroyNotify(self, event):
        self.logger.debug("onClientDestroyNotify: %r", event.__dict__)

        self.clientDestroyed = True

        self.onClosed()

        if self.clientWindowID is not None:
            try:
                singletons.wm.unmanageWindow(self)
            except:
                self.logger.exception("onClientDestroyNotify: Error unmanaging client window %r!", self.clientWindowID)

        self.unsubscribeFromEvents()

        if self.frameWindowID is not None:
            #TODO: Do we want to clear and save unused frames in a pool so we don't need to destroy and re-create them?
            try:
                xpybutil.conn.core.DestroyWindowChecked(self.frameWindowID).check()
            except:
                self.logger.exception("onClientDestroyNotify: Error destroying frame window %r!", self.frameWindowID)

        self.clientWindowID = None
        self.frameWindowID = None

    def onClosed(self):
        self.context = None
        if self.surface is not None:
            self.surface.finish()

        self.icccmState = icccm.State.Withdrawn

        # Emit 'closed' signal.
        self.closed()

    ## WM events ####
    def onGainedFocus(self):
        self.logger.debug("onGainedFocus")
        self.ewmhStates.add(EWMHWindowState.Focused)

        if self.frameWindowID is not None:
            self.applyTheme()

    def onLostFocus(self):
        self.logger.debug("onLostFocus")
        self.ewmhStates.discard(EWMHWindowState.Focused)

        if self.frameWindowID is not None:
            self.applyTheme()

    def onWorkspaceVisibilityChanged(self):
        if self.clientWindowID is None:
            self.logger.warn("onWorkspaceVisibilityChanged: No client window! PANIC!")

            try:
                # If you have objgraph and xdot installed, this will show an interactive backref graph.
                import objgraph
                objgraph.show_backrefs([self], refcounts=True, max_depth=20)
            except:
                pass

            import pprint
            pprint.pprint(dict(getattr(xpybutil.event, '__callbacks')))
            return

        if self.frameWindowID is None:
            self.logger.warn("onWorkspaceVisibilityChanged: No frame window! PANIC!")
            return

        if not self.workspace.visible:
            self.hide()

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
            try:
                self._workspace.visibilityChanged.disconnect(self.onWorkspaceVisibilityChanged)
            except KeyError:
                pass

        if workspace is None:
            # Remove the window's _NET_WM_DESKTOP property.
            #ewmh.remove_wm_desktop(self.clientWindowID)  # FIXME: xpybutil doesn't provide this!
            xpybutil.conn.core.DeleteProperty(self.clientWindowID, atom('_NET_WM_DESKTOP'))

            # Mark ourself as not viewable
            self.viewable = False

        else:
            # Update the window's _NET_WM_DESKTOP property.
            ewmh.set_wm_desktop(self.clientWindowID, workspace.index)

            # Mark ourself as viewable
            self.viewable = True

        oldWorkspace = self._workspace

        self._workspace = workspace
        self.addedToWorkspace = time.time()

        if oldWorkspace is not None:
            # Notify our old workspace that we've left. (we do this after changing self._workspace so the old one
            # doesn't try setting workspace to None)
            oldWorkspace.removeWindow(self)

        if workspace is not None:
            self.onWorkspaceVisibilityChanged()
            workspace.visibilityChanged.connect(self.onWorkspaceVisibilityChanged)

    @property
    def focused(self):
        return EWMHWindowState.Focused in self.ewmhStates

    @property
    def visible(self):
        return self.icccmState in (icccm.State.Withdrawn, icccm.State.Iconic)

    @property
    def valid(self):
        return self.initialized and not self.clientDestroyed

    @property
    def icccmState(self):
        return self._icccmState

    @icccmState.setter
    def icccmState(self, state):
        if self._icccmState == state:
            return

        self._icccmState = state
        self._updateICCCMState()

    @property
    def icccmIconWindowID(self):
        return self._icccmIconWindowID

    @icccmIconWindowID.setter
    def icccmIconWindowID(self, window):
        if self._icccmIconWindowID == window:
            return

        self._icccmIconWindowID = window
        self._updateICCCMState()

    ## Update Methods ####
    def _updateICCCMState(self):
        #TODO: Defer updates, so we only set WM_STATE once per event loop, even if both state and icon are updated
        if self.clientWindowID is not None:
            self.logger.trace("_updateICCCMState: Setting WM_STATE: state=%r, icon=%r",
                    self.icccmState, self.icccmIconWindowID)
            icccm.set_wm_state(self.clientWindowID, self.icccmState, self.icccmIconWindowID)

    def _updateEWMHState(self):
        #TODO: Defer updates, so we only set _NET_WM_STATE once per event loop, even if multiple changes are made
        if self.clientWindowID is not None:
            self.logger.trace("_updateEWMHState: Setting _NET_WM_STATE: %r", self.ewmhStates)
            ewmh.set_wm_state(self.clientWindowID, self.ewmhStates)

    def _updateLayoutInfo(self):
        #TODO: Defer updates, so we only set _FTTPWM_LAYOUT_INFO once per event loop, even if multiple changes are made
        #TODO: This should probably done through the X Session Management Protocol instead of using properties.
        if self.clientWindowID is not None:
            self.logger.trace("_updateLayoutInfo: Setting _FTTPWM_LAYOUT_INFO: %r", json.dumps(self.layoutInfo))
            self.setClientProperty(atom('_FTTPWM_LAYOUT_INFO'), json.dumps(self.layoutInfo))

    ## Visual Stuff ####
    def applyTheme(self):
        settings.theme.apply(self)

        singletons.eventloop.callWhenIdle(self.paint)

    def paint(self):
        if not self.initialized or self.frameWindowID is None or self.clientWindowID is None \
                or self.icccmState in (icccm.State.Withdrawn, icccm.State.Iconic) or self.context is None:
            # Skip painting.
            return

        self.context.set_operator(cairo.OPERATOR_OVER)

        tabs = self.workspace.layout.tabs(self)
        if tabs:
            self.logger.debug("paint: painting tabs in frame %r", self)
            tabSpacing, titlebarHeight = settings.theme.getFrameThemeValues(self, 'tabSpacing', 'titlebarHeight')

            tabWidth = (self.width - (tabSpacing * (len(tabs) - 1))) / len(tabs)
            tabX = 0

            # Draw the window border and our tab.
            ourIndex = tabs.index(self)
            ourTabGeom = [tabWidth * ourIndex, 0, tabWidth, titlebarHeight]
            settings.theme.paintWindow(self.context, self, ourTabGeom)

            # Draw other tabs.
            for tabbedFrame in tabs:
                if tabbedFrame is self:
                    # We already painted the tab for this frame; skip it.
                    continue

                tabGeom = [tabX, 0, tabWidth, titlebarHeight]
                self.logger.debug("paint: painting tab for %sframe %r at %r",
                        'focused ' if tabbedFrame.focused else '', tabbedFrame, tabGeom)

                settings.theme.paintTab(self.context, tabbedFrame, tabGeom)

                tabX += tabWidth + tabSpacing

        else:
            self.logger.debug("paint: painting full window for frame %r", self)
            settings.theme.paintWindow(self.context, self)

        self.surface.flush()
