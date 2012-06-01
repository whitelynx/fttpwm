# -*- coding: utf-8 -*-
"""FTTPWM: Main application

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from collections import deque
import datetime
import logging
import operator
import os
import struct
import sys
import time

import xcb
from xcb.xproto import Atom, CW, ConfigWindow, EventMask, InputFocus, PropMode, SetMode, StackMode, WindowClass
from xcb.xproto import CirculateRequestEvent, ConfigureRequestEvent, MapRequestEvent
from xcb.xproto import ConfigureNotifyEvent, MappingNotifyEvent

import xpybutil
import xpybutil.event
import xpybutil.ewmh as ewmh
from xpybutil.util import get_atom as atom
import xpybutil.window

from .ewmh import EWMHAction, EWMHWindowState, EWMHWindowType
from .settings import settings
from .setroot import setWallpaper
from .utils import convertAttributes, findCurrentVisual
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


class Color(object):
    @staticmethod
    def float(*components):
        return map(lambda x: int(x * 2 ** 16), components)


class WM(object):
    class RecurringEvent(object):
        def __init__(self, interval, callback):
            self.interval, self.callback = interval, callback
            self.nextCall = datetime.datetime.now() + interval

        def check(self):
            try:
                if datetime.datetime.now() > self.nextCall:
                    self()
            except StopIteration:
                # Leave the timer queue.
                return None

            # Stay in the timer queue.
            return self

        def __call__(self):
            self.callback()
            self.nextCall = datetime.datetime.now() + self.interval

    def __init__(self):
        self.pid = os.getpid()

        self.startupFinished = False
        self.onStartup = Signal()
        self.timers = deque()
        self.whenQueueEmpty = set()

        assert singletons.wm is None
        singletons.wm = self

        self.setup = xpybutil.conn.get_setup()
        self.screenNumber = xpybutil.conn.pref_screen
        self.screen = self.setup.roots[self.screenNumber]
        self.root = self.screen.root
        self.depth = self.screen.root_depth
        self.visualID = self.screen.root_visual
        self.visual = findCurrentVisual(self.screen, self.depth, self.visualID)
        self.screenWidth = self.screen.width_in_pixels
        self.screenHeight = self.screen.height_in_pixels
        self.colormap = self.screen.default_colormap

        self.white = self.screen.white_pixel
        self.black = self.screen.black_pixel

        self.windows = SignaledDict()
        self.windows.updated.connect(self.updateWindowList)

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

        self.workspaces = WorkspaceManager(self)

        self.focusedWindow = None

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

            return struts

    def allocColor(self, color):
        """Allocate the given color and return its XID.

        `color` must be a tuple `(r, g, b)` where `r`, `g`, and `b` are between 0 and 1.

        """
        return xpybutil.conn.core.AllocColor(self.colormap, *color).reply().pixel

    def checkForOtherWMs(self):
        logger.debug("Checking for other window managers...")
        try:
            xpybutil.conn.core.ChangeWindowAttributesChecked(self.root, *convertAttributes({
                    CW.EventMask: EventMask.SubstructureRedirect
                    })).check()
        except:
            logger.exception("Another window manager is already running! Exiting.")
            sys.exit(1)

    def startManaging(self):
        logger.debug("startManaging: Initializing EWMH compliance.")

        self.ewmhChildWindow, cookie = self.createWindow(0, 0, 1, 1,
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

        xpybutil.event.connect('MapRequest', self.root, self.onMapRequest)
        xpybutil.event.connect('MapNotify', self.root, self.onMapNotify)

        logger.debug("startManaging: Reticulating splines.")

        xpybutil.window.listen(self.root, 'PropertyChange',
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
                    atom('WM_S{}'.format(self.screenNumber)),
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
        ewmh.set_supporting_wm_check(self.root, self.ewmhChildWindow)
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
                #atom('_NET_REQUEST_FRAME_EXTENTS'),  # TODO: Handle this: set the given window's _NET_FRAME_EXTENTS.
                #   requests from pagers, etc.
                #atom('_NET_CLOSE_WINDOW'),
                #atom('_NET_MOVERESIZE_WINDOW'),
                #atom('_NET_RESTACK_WINDOW'),

                # Application Window Properties
                #   set by WM
                atom('_NET_WM_DESKTOP'),  # Also may be set by client before initially mapping window
                atom('_NET_WM_STATE'), atom('_NET_WM_ALLOWED_ACTIONS'),
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

    def createWindow(self, x, y, width, height, attributes={}, windowID=None, parentID=None, borderWidth=0,
            windowClass=WindowClass.InputOutput, checked=False):
        """A convenience method to create a new window.

        The major advantage of this is the ability to use a dictionary to specify window attributes; this eliminates
        the need to figure out what order to specify values in according to the numeric values of the 'CW' or
        'ConfigWindow' enum members you're using.

        """
        if windowID is None:
            windowID = xpybutil.conn.generate_id()

        if parentID is None:
            parentID = self.root

        attribMask = 0
        attribValues = list()

        # Values must be sorted by CW or ConfigWindow enum value, ascending.
        # Luckily, the tuples we get from dict.iteritems will automatically sort correctly.
        for attrib, value in sorted(attributes.iteritems()):
            attribMask |= attrib
            attribValues.append(value)

        if checked:
            call = xpybutil.conn.core.CreateWindowChecked
        else:
            call = xpybutil.conn.core.CreateWindow

        cookie = call(
                self.depth,
                windowID, parentID,
                x, y, width, height,
                borderWidth, windowClass,
                self.visualID,
                attribMask, attribValues
                )

        if checked:
            return windowID, cookie
        else:
            return windowID

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

        frame = WindowFrame(self, clientWindowID)
        logger.debug("manageWindow: Created new frame: %r", frame)

        self.windows[clientWindowID] = frame

    def unmanageWindow(self, frame):
        if frame.clientWindowID not in self.windows:
            logger.warn("unmanageWindow: client window of %r is not a recognized client! Ignoring call.", frame)
            return

        logger.debug("unmanageWindow: Unmanaging client window of %r...", frame)

        del self.windows[frame.clientWindowID]
        self.workspaces.removeWindow(frame)

    def focusWindow(self, frame):
        logger.debug("focusWindow: Focusing %r.", frame)

        if self.focusedWindow is not None:
            try:
                self.focusedWindow.onLostFocus()
            except:
                logger.exception("focusWindow: Error calling onLostFocus on %r.", self.focusedWindow)

        self.focusedWindow = frame

        xpybutil.conn.core.SetInputFocus(InputFocus.PointerRoot, frame.clientWindowID, xcb.CurrentTime)
        ewmh.set_active_window(frame.clientWindowID)

        try:
            frame.onGainedFocus()
        except:
            logger.exception("focusWindow: Error calling onGainedFocus on %r.", self.focusedWindow)

        xpybutil.conn.flush()

    ## Managed windows ####
    def updateWindowList(self):
        ewmh.set_client_list(self.windows)
        ewmh.set_client_list_stacking(self.windows)

    ## Event handlers ####
    def onSelectionRequest(self, event):
        logger.debug("onSelectionRequest:\n  %s", "\n  ".join(map(repr, event.__dict__.items())))
        mask = EventMask.NoEvent
        replyEvent = SelectionNotifyEvent.build()
        xpybutil.event.send_event(event.requestor, mask, replyEvent)
        event.SendEvent(false, event.requestor, EventMask.NoEvent, replyEvent)

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
            logger.debug("manageWindow: Window %r is already in our list of clients; notifying existing frame.",
                    clientWindowID)

        self.windows[clientWindowID].onClientMapRequest()

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

    def callEvery(self, interval, callback):
        self.timers.append(self.RecurringEvent(interval, callback))

    def callWhenQueueEmpty(self, callback):
        self.whenQueueEmpty.add(callback)

    ## Main event loop ####
    def run(self):
        logger.info("Starting main event loop.")

        #NOTE: This does several things that xpybutil.event.main doesn't do:
        # - It ensures that the WM gets MapRequest events, and windows get SelectionRequest when appropriate.
        # - It implements crude timers so various things can register a callback to happen every `n` seconds, or once
        #   after `n` seconds.
        # - It implements callWhenQueueEmpty, which effectively runs a callback when we're idle.
        try:
            while True:
                #FIXME: Find a better way to do timeouts than polling and sleeping! It'd be preferable to block, if we
                # could set a timeout on the blocking call.
                #xpybutil.event.read(block=True)
                xpybutil.event.read(block=False)

                # Check if there are any waiting events.
                if len(xpybutil.event.peek()) == 0:
                    # Run all the callbacks in whenQueueEmpty, and clear it.
                    for callback in self.whenQueueEmpty:
                        callback()

                    self.whenQueueEmpty.clear()

                    #XXX: HACK: Sleep 10ms, so we can check for wakeups at least that often.
                    time.sleep(0.01)

                for e in xpybutil.event.queue():
                    w = None
                    if isinstance(e, MappingNotifyEvent):
                        # MappingNotify events get sent to the xpybutil.keybind.update_keyboard_mapping function, to
                        # update the stored keyboard mapping.
                        w = None
                    elif isinstance(e, (CirculateRequestEvent, ConfigureRequestEvent, MapRequestEvent)):
                        # Send all SubstructureRedirect *Request events to the parent window, which should be the
                        # window which had the SubstructureRedirect mask set on it. (that is, if i'm reading the docs
                        # correctly)
                        w = e.parent
                    elif hasattr(e, 'event'):
                        w = e.event
                    elif hasattr(e, 'window'):
                        w = e.window
                    elif hasattr(e, 'owner'):
                        w = e.owner
                    elif hasattr(e, 'requestor'):
                        w = e.requestor

                    key = (e.__class__, w)
                    for cb in getattr(xpybutil.event, '__callbacks').get(key, []):
                        try:
                            cb(e)
                        except Exception:
                            logger.exception("Error while calling callback %r for %r event on %r! Continuing...",
                                    cb, e.__class__, w)

                    #XXX: Debugging...
                    #if isinstance(e, ConfigureNotifyEvent):
                    #    logger.debug("Got ConfigureNotifyEvent: %r; w=%r; listeners: %r",
                    #            e.__dict__, w, getattr(xpybutil.event, '__callbacks').get(key, []))
                    #if isinstance(e, MapRequestEvent):
                    #    logger.debug("Got MapRequestEvent: %r; w=%r; listeners: %r",
                    #            e.__dict__, w, getattr(xpybutil.event, '__callbacks').get(key, []))

                xpybutil.conn.flush()

                for timer in self.timers:
                    # If the timer's 'check' method returns None, remove it from the queue.
                    if timer.check() is None:
                        self.timers.remove(timer)

        except xcb.Exception:
            logger.exception("Error in main event loop! Exiting with error status.")
            sys.exit(1)

        logger.info("Event loop terminated; shutting down normally.")
