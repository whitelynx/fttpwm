# -*- codin-g: utf-8 -*-
"""FTTPWM: Main application

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from collections import deque
import logging
import os
import struct
import weakref

import xcb
from xcb.xproto import Atom, CW, EventMask, InputFocus, PropMode, SetMode

import xpybutil
import xpybutil.event
import xpybutil.ewmh as ewmh
from xpybutil.util import get_atom as atom
import xpybutil.window

from .ewmh import EWMHAction, EWMHWindowState, EWMHWindowType
from .settings import settings
from .setroot import setWallpaper
from .utils import convertAttributes
from .xevents import SelectionNotifyEvent
from .frame import WindowFrame
from .signals import Signal
from .signaled import SignaledDict
from .statusbar import StatusBar
from .workspace import WorkspaceManager
from . import singletons


logger = logging.getLogger("fttpwm.wm")

settings.setDefaults(
        autostart=[]
        )


class WM(object):
    def __init__(self):
        self.pid = os.getpid()

        self.startupFinished = False
        self.onStartup = Signal()
        self.timers = deque()
        self.whenQueueEmpty = set()

        assert singletons.wm is None
        singletons.wm = self

        self.windows = SignaledDict()
        self.windows.updated.connect(self.updateWindowList)

        self.frameWindows = weakref.WeakValueDictionary()

        # Start with no global (non-workspace-specific / "pinned") struts.
        #TODO: Take Xinerama/XRandR dead spaces into account!
        #TODO: Detect windows with _NET_WM_STRUT or _NET_WM_STRUT_PARTIAL set!
        self.strutsLeft = SignaledDict()
        self.strutsRight = SignaledDict()
        self.strutsTop = SignaledDict()
        self.strutsBottom = SignaledDict()

        self.struts = {
                'left': self.strutsLeft,
                'right': self.strutsRight,
                'top': self.strutsTop,
                'bottom': self.strutsBottom
                }

        self._lastFocusedWindow = None

        self.workspaces = WorkspaceManager()
        self.workspaces.currentChanged.connect(self.onWorkspaceChanged)

        try:
            from fttpwm.control import RemoteControlServer
            self.remoteServer = RemoteControlServer()

        except ImportError:
            logger.warn("Error importing RemoteControlServer; no remote control available!", exc_info=True)

        self.checkForOtherWMs()
        self.startManaging()
        settings.loadSettings()
        setWallpaper()

        logger.info("Running autostart commands...")
        for startAction in settings.autostart:
            startAction()
        logger.info("Finished running autostart commands.")

        self.startupFinished = True
        logger.info("Running startup callbacks...")

        self.onStartup()

        StatusBar.startIfConfigured()

        logger.info("Finished running startup callbacks.")

    def whenStartupFinished(self, callback):
        if self.startupFinished:
            callback()
        else:
            self.onStartup.connect(callback)

    def _doFocus(self, frame):
        xpybutil.conn.core.SetInputFocus(InputFocus.PointerRoot, frame.clientWindowID, xcb.CurrentTime)
        ewmh.set_active_window(frame.clientWindowID)

        try:
            frame.onGainedFocus()
        except:
            logger.exception("focusWindow: Error calling onGainedFocus on %r.", frame)

        xpybutil.conn.flush()

        self.lastFocusedWindow = frame

    def onWorkspaceChanged(self):
        frame = self.focusedWindow
        if frame is not None:
            logger.debug("Workspace changed; setting input focus to %r.", frame)

            self._doFocus(frame)

    @property
    def focusedWindow(self):
        return self.workspaces.current.focusedWindow

    @focusedWindow.setter
    def focusedWindow(self, frame):
        if self.lastFocusedWindow is not None:
            try:
                self.lastFocusedWindow.onLostFocus()
            except:
                logger.exception("focusWindow: Error calling onLostFocus on %r.", self.lastFocusedWindow)

        if frame is None and self.workspaces.current.focusedWindow is not None:
            logger.warn("Setting workspace %r's focused window to None! (used to be %r)",
                    self.workspaces.current, self.workspaces.current.focusedWindow)
        self.workspaces.current.focusedWindow = frame

        if frame is None:
            self.lastFocusedWindow = None
        else:
            self._doFocus(frame)

    @property
    def lastFocusedWindow(self):
        if self._lastFocusedWindow is not None:
            return self._lastFocusedWindow()

    @lastFocusedWindow.setter
    def lastFocusedWindow(self, frame):
        if isinstance(frame, weakref.ReferenceType):
            self._lastFocusedWindow = frame
        else:
            self._lastFocusedWindow = weakref.ref(frame)

    @property
    def strutsLeftSize(self):
        return sum(self.strutsLeft.values())

    @property
    def strutsRightSize(self):
        return sum(self.strutsRight.values())

    @property
    def strutsTopSize(self):
        return sum(self.strutsTop.values())

    @property
    def strutsBottomSize(self):
        return sum(self.strutsBottom.values())

    def getWindowStruts(self, windowID):
        wmPartialStrutCookie = ewmh.get_wm_strut_partial(windowID)
        wmStrutCookie = ewmh.get_wm_strut(windowID)

        wmPartialStrut = wmPartialStrutCookie.reply()
        wmStrut = wmStrutCookie.reply()

        if wmPartialStrut is not None:
            return wmPartialStrut

        elif wmStrut is not None:
            # Convert WM_STRUT to the equivalent WM_PARTIAL_STRUT.
            struts = {
                    'left': 0,
                    'right': 0,
                    'top': 0,
                    'bottom': 0,
                    'left_start_y': 0,
                    'left_end_y': 0,
                    'right_start_y': 0,
                    'right_end_y': 0,
                    'top_start_x': 0,
                    'top_end_x': 0,
                    'bottom_start_x': 0,
                    'bottom_end_x': 0
                    }

            struts.update(wmStrut)

            fullSize = {
                    'x': singletons.x.screenWidth,
                    'y': singletons.x.screenHeight,
                    }
            for side, dimension in {'left': 'y', 'right': 'y', 'top': 'x', 'bottom': 'x'}.iteritems():
                if struts[side] > 0:
                    struts[side + '_end_' + dimension] = fullSize[dimension]

            return struts

    def checkForOtherWMs(self):
        logger.debug("Checking for other window managers...")
        try:
            xpybutil.conn.core.ChangeWindowAttributesChecked(singletons.x.root, *convertAttributes({
                    CW.EventMask: EventMask.SubstructureRedirect
                    })).check()
        except:
            logger.exception("Another window manager is already running! Exiting.")
            singletons.eventloop.exit(1)

    def startManaging(self):
        logger.debug("startManaging: Initializing EWMH compliance.")

        self.ewmhChildWindow, cookie = singletons.x.createWindow(0, 0, 1, 1,
                attributes={
                    CW.OverrideRedirect: 1
                    },
                checked=True
                )
        cookie.check()

        self.setWMChildProps()
        self.setRootProps()
        self.workspaces.setEWMHProps()

        logger.debug("startManaging: Subscribing to events.")

        xpybutil.event.connect('MapRequest', singletons.x.root, self.onMapRequest)
        xpybutil.event.connect('MapNotify', singletons.x.root, self.onMapNotify)

        logger.debug("startManaging: Reticulating splines.")

        xpybutil.window.listen(singletons.x.root, 'PropertyChange',
                'SubstructureRedirect', 'SubstructureNotify', 'StructureNotify')

    def setWMChildProps(self):
        logger.debug(
                "Setting up _NET_SUPPORTING_WM child window for EWMH compliance. (ID=%r, _NET_WM_PID=%r, "
                "_NET_WM_NAME=%r, _NET_SUPPORTING_WM_CHECK=%r)",
                self.ewmhChildWindow, self.pid, 'FTTPWM', self.ewmhChildWindow
                )

        def acquireWMScreenSelection(event):
            # Acquire WM_Sn selection. (ICCCM window manager requirement) According to ICCCM, you should _not_ use
            # CurrentTime here, but instead the 'time' field of a recent event, so that's what we're doing.
            xpybutil.conn.core.SetSelectionOwner(
                    self.ewmhChildWindow,
                    atom('WM_S{}'.format(singletons.x.screenNumber)),
                    event.time
                    )

            try:
                xpybutil.window.listen(self.ewmhChildWindow)
            except:
                self.logger.exception("Error while clearing listened events on _NET_SUPPORTING_WM child window %r!",
                        self.ewmhChildWindow)

            xpybutil.event.disconnect('PropertyNotify', self.ewmhChildWindow)
            # Leave SelectionRequest connected, since we will continue to receive it even after clearing the listened
            # events, and since we need to continue to respond with the correct message when asked.

        xpybutil.event.connect('PropertyNotify', self.ewmhChildWindow, acquireWMScreenSelection)
        xpybutil.event.connect('SelectionRequest', self.ewmhChildWindow, self.onSelectionRequest)

        xpybutil.window.listen(self.ewmhChildWindow, 'PropertyChange')

        ewmh.set_wm_name(self.ewmhChildWindow, 'FTTPWM')
        ewmh.set_supporting_wm_check(self.ewmhChildWindow, self.ewmhChildWindow)

        try:
            ewmh.set_wm_pid(self.ewmhChildWindow, self.pid)
        except OverflowError:
            #XXX: HACK to work around broken code in xpybutil.ewmh:
            packed = struct.pack('I', self.pid)
            xpybutil.conn.core.ChangeProperty(PropMode.Replace, self.ewmhChildWindow, atom('_NET_WM_PID'),
                    Atom.CARDINAL, 32, 1, packed)
            #/HACK

    def setRootProps(self):
        ewmh.set_supporting_wm_check(singletons.x.root, self.ewmhChildWindow)
        ewmh.set_supported([
                # Root Window Properties (and Related Messages)
                atom('_NET_SUPPORTED'),
                atom('_NET_CLIENT_LIST'), atom('_NET_CLIENT_LIST_STACKING'),
                atom('_NET_NUMBER_OF_DESKTOPS'),
                atom('_NET_DESKTOP_GEOMETRY'), atom('_NET_DESKTOP_VIEWPORT'), atom('_NET_CURRENT_DESKTOP'),
                atom('_NET_DESKTOP_NAMES'), atom('_NET_ACTIVE_WINDOW'), atom('_NET_WORKAREA'),
                atom('_NET_SUPPORTING_WM_CHECK'),
                #atom('_NET_VIRTUAL_ROOTS'), atom('_NET_DESKTOP_LAYOUT'), atom('_NET_SHOWING_DESKTOP'),

                # Other Root Window Messages
                #   requests from client
                #atom('_NET_WM_MOVERESIZE'),
                #atom('_NET_REQUEST_FRAME_EXTENTS'),  # TODO: Handle this: calculate given window's _NET_FRAME_EXTENTS.
                #   requests from pagers, etc.
                #atom('_NET_CLOSE_WINDOW'),
                #atom('_NET_MOVERESIZE_WINDOW'),
                #atom('_NET_RESTACK_WINDOW'),

                # Application Window Properties
                #   set by WM
                atom('_NET_WM_ALLOWED_ACTIONS'),
                atom('_NET_WM_DESKTOP'), atom('_NET_WM_STATE'),  # Also may be set by client before initially mapping
                #   set by client
                atom('_NET_WM_NAME'), atom('_NET_WM_ICON_NAME'),
                atom('_NET_WM_WINDOW_TYPE'),
                atom('_NET_WM_PID'), atom('WM_CLIENT_MACHINE'),  # Support for killing hung processes
                atom('_NET_FRAME_EXTENTS'),
                #atom('_NET_WM_VISIBLE_NAME'), atom('_NET_WM_VISIBLE_ICON_NAME'),  # TODO: Elide titles, and set these!
                atom('_NET_WM_STRUT'), atom('_NET_WM_STRUT_PARTIAL'),
                #atom('_NET_WM_ICON_GEOMETRY'), atom('_NET_WM_ICON'),
                #atom('_NET_WM_USER_TIME'),  # TODO: Support for user activity tracking and startup notification
                #   set by pagers, etc.
                #atom('_NET_WM_HANDLED_ICONS'),  # Support for taskbars/pagers that display icons for iconified windows

                # Window Manager Protocols
                #atom('_NET_WM_PING'),  # Support for killing hung processes
                #atom('_NET_WM_SYNC_REQUEST'),

                # _NET_WM_ALLOWED_ACTIONS values
                EWMHAction.Move, EWMHAction.Resize, EWMHAction.Close,
                #EWMHAction.Minimize, EWMHAction.Shade, EWMHAction.Stick, EWMHAction.MaximizeHorz,
                #EWMHAction.MaximizeVert, EWMHAction.Fullscreen, #EWMHAction.ChangeDesktop,

                # _NET_WM_STATE values
                EWMHWindowState.MaximizedVert, EWMHWindowState.MaximizedHorz,
                #EWMHWindowState.Modal, EWMHWindowState.Sticky, EWMHWindowState.Shaded, EWMHWindowState.SkipTaskbar,
                #EWMHWindowState.SkipPager, EWMHWindowState.Hidden, EWMHWindowState.Fullscreen, EWMHWindowState.Above,
                #EWMHWindowState.Below, EWMHWindowState.DemandsAttention,

                # _NET_WM_WINDOW_TYPE values
                EWMHWindowType.Normal,
                #EWMHWindowType.Desktop, EWMHWindowType.Dock, EWMHWindowType.Toolbar, EWMHWindowType.Menu,
                #EWMHWindowType.Utility, EWMHWindowType.Splash, EWMHWindowType.Dialog,
                ])

    ## Individual client management ####
    def manageWindow(self, clientWindowID):
        if clientWindowID in self.windows:
            logger.warn("manageWindow: Window %r is already in our list of clients; ignoring.", clientWindowID)
            return

        logger.debug("manageWindow: Managing window %r...", clientWindowID)

        cookies = []
        cookies.append(xpybutil.conn.core.ChangeSaveSetChecked(SetMode.Insert, clientWindowID))

        #FIXME: Move into WorkspaceManager.placeOnWorkspace!
        #FIXME: We should pay attention to the _NET_WM_DESKTOP value if initially set by the client, and try to put the
        # window on that desktop. If it is not set, or the specified desktop doesn't exist, then we should set it.
        #ewmh.get_wm_desktop(clientWindowID)
        ewmh.set_wm_desktop(clientWindowID, 0)

        frame = WindowFrame(clientWindowID)
        logger.debug("manageWindow: Created new frame: %r", frame)

        self.windows[clientWindowID] = frame

    def unmanageWindow(self, frame):
        if frame.clientWindowID not in self.windows:
            logger.warn("unmanageWindow: client window of %r is not a recognized client! Ignoring call.", frame)
            return

        logger.debug("unmanageWindow: Unmanaging client window of %r...", frame)

        del self.windows[frame.clientWindowID]
        del self.frameWindows[frame.frameWindowID]
        self.workspaces.removeWindow(frame)

    def focusWindow(self, frame):
        logger.debug("focusWindow: Focusing %r.", frame)

        self.focusedWindow = frame

    ## Managed windows ####
    def updateWindowList(self):
        ewmh.set_client_list(self.windows)
        ewmh.set_client_list_stacking(self.windows)

    def getFrame(self, winID):
        frame = self.windows.get(winID, None)

        if frame is None:
            frame = self.frameWindows.get(winID, None)

        return frame

    ## Event handlers ####
    def onSelectionRequest(self, event):
        logger.debug("onSelectionRequest:\n  %s", "\n  ".join(map(repr, event.__dict__.items())))
        mask = EventMask.NoEvent
        replyEvent = SelectionNotifyEvent.build()
        xpybutil.event.send_event(event.requestor, mask, replyEvent)
        event.SendEvent(False, event.requestor, EventMask.NoEvent, replyEvent)

    def onMapRequest(self, event):
        clientWindowID = event.window
        logger.debug("onMapRequest: %r", clientWindowID)

        struts = self.getWindowStruts(clientWindowID)
        if struts is not None:
            logger.debug("onMapRequest: Found struts on window; skipping window management.")

            try:
                xpybutil.conn.core.MapWindowChecked(clientWindowID).check()
            except:
                logger.exception("onMapRequest: Error mapping client window %r!", clientWindowID)

        elif clientWindowID not in self.windows:
            # If we don't already have a frame for this client, create one.
            self.manageWindow(clientWindowID)

        else:
            logger.debug("onMapRequest: Window %r is already in our list of clients; notifying existing frame.",
                    clientWindowID)

        frame = self.windows[clientWindowID]
        frame.onClientMapRequest()
        self.frameWindows[frame.frameWindowID] = frame

    def onMapNotify(self, event):
        clientWindowID = event.window
        logger.debug("onMapNotify: %r", clientWindowID)

        struts = self.getWindowStruts(clientWindowID)
        logger.debug("Struts: %r", struts)
        if struts is not None:
            for side in 'left right top bottom'.split():
                if struts[side] > 0:
                    logger.debug("onMapNotify: Found strut on %s side: %s", side, struts[side])
                    self.struts[side][clientWindowID] = struts[side]

            # Listen for UnmapNotify events so we can ditch the struts when the window unmaps.
            xpybutil.window.listen(clientWindowID, 'StructureNotify')
            xpybutil.event.connect('UnmapNotify', clientWindowID, self.onUnmapNotify)

    def onUnmapNotify(self, event):
        clientWindowID = event.window
        #logger.trace("onUnmapNotify: %r", clientWindowID)  # This is REALLY noisy.

        for side in 'left right top bottom'.split():
            if clientWindowID in self.struts[side]:
                del self.struts[side][clientWindowID]
