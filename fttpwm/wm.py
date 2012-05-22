# -*- coding: utf-8 -*-
"""FTTPWM: Main application

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import logging
import os
import struct
import sys

import xcb
from xcb.xproto import Atom, CW, ConfigWindow, EventMask, InputFocus, PropMode, SetMode, StackMode, WindowClass
from xcb.xproto import MappingNotifyEvent, MapRequestEvent

import xpybutil
import xpybutil.event
import xpybutil.ewmh as ewmh
from xpybutil.util import get_atom as atom
import xpybutil.window

from .ewmh import EWMHAction, EWMHWindowState, EWMHWindowType
from .settings import settings
from .utils import convertAttributes
from .xevents import SelectionNotifyEvent
from .frame import WindowFrame


logger = logging.getLogger("fttpwm.wm")

settings.setDefaults(
        desktops=[
            'alpha',
            'beta',
            'gamma',
            'delta',
            'pi',
            'omega',
            'phlange',
            'dromedary',
            '°±²ÛÝÜßÞÛ²±°',
            'û©ýðñ«ü¡',
            'õõõõõõõõõõõõõõõõõõ',
            'àáçëãê¯Ù§',
            '¢Ã¿ªØ',
            'äë¡áÀ£ ïüDîÚê3àr',
            '¨ª¦¥¤£¢³ºÄÍÃÇÌÁÏÐÊØÎÒÑË´µ¶¹¿·¸»ÚÕÖÉ½¼¾ÙÀ­úöìíøïõéäîòõù®¬§àáçëãê¯',
            ],
        initialDesktop=0,
        )


class Color(object):
    @staticmethod
    def float(*components):
        return map(lambda x: int(x * 2 ** 16), components)


class WM(object):
    def __init__(self):
        self.pid = os.getpid()

        self.setup = xpybutil.conn.get_setup()
        self.screenNumber = xpybutil.conn.pref_screen
        self.screen = self.setup.roots[self.screenNumber]
        self.root = self.screen.root
        self.depth = self.screen.root_depth
        self.visualID = self.screen.root_visual
        self.visual = self.findCurrentVisual()
        self.desktopWidth = self.screen.width_in_pixels
        self.desktopHeight = self.screen.height_in_pixels
        self.colormap = self.screen.default_colormap

        self.white = self.screen.white_pixel
        self.black = self.screen.black_pixel

        self.focusedBorderColor = self.allocColor(Color.float(.25, .5, 0))
        self.unfocusedBorderColor = self.allocColor(Color.float(.25, .25, .25))

        self.windows = dict()
        self.focusedWindow = None

        self.checkForOtherWMs()
        self.startManaging()
        settings.loadSettings()

    def findCurrentVisual(self):
        """Find the VISUALTYPE object for our current visual.

        This is needed for initializing a Cairo XCBSurface.

        """
        for depth in self.screen.allowed_depths:
            if depth.depth == self.depth:
                for visual in depth.visuals:
                    if visual.visual_id == self.visualID:
                        return visual

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
        self.setDesktopProps()

        logger.debug("startManaging: Subscribing to events.")

        xpybutil.window.listen(xpybutil.root, 'EnterWindow', 'LeaveWindow', 'PropertyChange',
                'SubstructureRedirect', 'SubstructureNotify', 'StructureNotify')
                # It might make sense to do this, but if we update our frames when we set the focus, it'll be faster.
                #'EventMask.FocusChange')

        logger.debug("startManaging: Reticulating splines.")

        xpybutil.event.connect('EnterNotify', self.root, self.onEnterNotify)
        xpybutil.event.connect('MapRequest', self.root, self.onMapRequest)

    def setWMChildProps(self):
        logger.debug(
                "Setting up _NET_SUPPORTING_WM child window for EWMH compliance. (ID=%r, _NET_WM_PID=%r, "
                "_NET_WM_NAME=%r, _NET_SUPPORTING_WM_CHECK=%r)",
                self.ewmhChildWindow, self.pid, 'FTTPWM', self.ewmhChildWindow
                )

        def acquireWMScreenSelection(event):
            # Acquire WM_Sn selection. (ICCCM window manager requirement) According to ICCCM, you should _not_ use
            # CurrentTime here, but instead the 'time' field of a recent event, so that's what we're doing.
            xpybutil.conn.core.SetSelectionOwner(self.ewmhChildWindow, atom('WM_S{}'.format(self.screenNumber)),
                    event.time)
            xpybutil.event.disconnect('PropertyNotify', self.ewmhChildWindow)
            xpybutil.window.listen(self.ewmhChildWindow)

        xpybutil.window.listen(self.ewmhChildWindow, 'PropertyChange')
        xpybutil.event.connect('PropertyNotify', self.ewmhChildWindow, acquireWMScreenSelection)
        xpybutil.event.connect('SelectionRequest', self.ewmhChildWindow, self.onSelectionRequest)

        ewmh.set_wm_name(self.ewmhChildWindow, 'FTTPWM')
        ewmh.set_supporting_wm_check(self.ewmhChildWindow, self.ewmhChildWindow)

        try:
            ewmh.set_wm_pid(self.ewmhChildWindow, self.pid)
        except OverflowError:
            #XXX: HACK to work around broken code in xpybutil.ewmh:
            packed = struct.pack('I', pid)
            xpybutil.conn.core.ChangeProperty(PropMode.Replace, self.ewmhChildWindow, atom('_NET_WM_PID'),
                    Atom.CARDINAL, 32, 1, packed)
            #/HACK

    def setRootProps(self):
        ewmh.set_supporting_wm_check(self.root, self.ewmhChildWindow)
        ewmh.set_supported([
                # Root Window Properties (and Related Messages)
                atom('_NET_SUPPORTED'), atom('_NET_CLIENT_LIST'), atom('_NET_NUMBER_OF_DESKTOPS'),
                atom('_NET_DESKTOP_GEOMETRY'), atom('_NET_DESKTOP_VIEWPORT'), atom('_NET_CURRENT_DESKTOP'),
                atom('_NET_DESKTOP_NAMES'), atom('_NET_ACTIVE_WINDOW'), atom('_NET_WORKAREA'),
                atom('_NET_SUPPORTING_WM_CHECK'),
                #atom('_NET_VIRTUAL_ROOTS'), atom('_NET_DESKTOP_LAYOUT'), atom('_NET_SHOWING_DESKTOP'),

                # Other Root Window Messages
                #atom('_NET_CLOSE_WINDOW'), atom('_NET_MOVERESIZE_WINDOW'), atom('_NET_WM_MOVERESIZE'),
                #atom('_NET_RESTACK_WINDOW'), atom('_NET_REQUEST_FRAME_EXTENTS'),

                # Application Window Properties
                atom('_NET_WM_NAME'), atom('_NET_WM_ICON_NAME'), atom('_NET_WM_DESKTOP'), atom('_NET_WM_WINDOW_TYPE'),
                atom('_NET_WM_STATE'), atom('_NET_WM_ALLOWED_ACTIONS'), atom('_NET_WM_PID'),
                atom('_NET_FRAME_EXTENTS'),
                #atom('_NET_WM_VISIBLE_NAME'), atom('_NET_WM_VISIBLE_ICON_NAME'), atom('_NET_WM_STRUT'),
                #atom('_NET_WM_STRUT_PARTIAL'), atom('_NET_WM_ICON_GEOMETRY'), atom('_NET_WM_ICON'),
                #atom('_NET_WM_HANDLED_ICONS'), atom('_NET_WM_USER_TIME'),

                # Window Manager Protocols
                #atom('_NET_WM_PING'), atom('_NET_WM_SYNC_REQUEST'),

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

    def setDesktopProps(self):
        desktops = settings.desktops
        ewmh.set_desktop_names(settings.desktops)
        ewmh.set_number_of_desktops(len(settings.desktops))
        ewmh.set_current_desktop(settings.initialDesktop)
        ewmh.set_desktop_geometry(self.desktopWidth, self.desktopHeight)
        ewmh.set_workarea(
                [{'x': 0, 'y': 0, 'width': self.desktopWidth, 'height': self.desktopHeight}] * len(settings.desktops)
                )
        ewmh.set_desktop_viewport(
                [{'x': 0, 'y': 0}] * len(settings.desktops)
                )

    def createWindow(self, x, y, width, height, attributes={}, windowID=None, parentID=None, borderWidth=0,
            windowClass=WindowClass.InputOutput, checked=False):
        """A convenience method to create new windows.

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

    def manageWindow(self, clientWindow):
        if clientWindow in self.windows:
            logger.warn("manageWindow: Window %r is already in our list of clients! Ignoring call.", clientWindow)
            return

        logger.debug("Managing window %r...", clientWindow)

        cookies = []
        cookies.append(xpybutil.conn.core.ChangeSaveSetChecked(SetMode.Insert, clientWindow))

        #FIXME: We should pay attention to the _NET_WM_DESKTOP value if initially set by the client, and try to put the
        # window on that desktop. If it is not set, or the specified desktop doesn't exist, then we should set it.
        #ewmh.get_wm_desktop(clientWindow)
        ewmh.set_wm_desktop(clientWindow, 0)

        frame = WindowFrame(self, clientWindow)

        self.windows[clientWindow] = frame
        self.updateWindows()

    def unmanageWindow(self, clientWindow):
        if clientWindow not in self.windows:
            logger.warn("unmanageWindow: Window %r is not in our list of clients! Ignoring call.", clientWindow)
            return

        logger.debug("Unmanaging window %r...", clientWindow)

        #TODO: Move into Frame.
        # Stop handling events from this window.
        xpybutil.event.disconnect('EnterNotify', clientWindow)
        xpybutil.event.disconnect('UnmapNotify', clientWindow)
        # [end Move into Frame]

        del self.windows[clientWindow]
        self.updateWindows()

    def updateWindows(self):
        ewmh.set_client_list(self.windows)
        self.rearrangeWindows()

    def rearrangeWindows(self):
        windowCount = len(self.windows)
        if windowCount == 0:
            return

        x = 0
        y = 0
        width = self.desktopWidth / windowCount
        height = self.desktopHeight

        for frame in self.windows.values():
            #TODO: Move this into WindowFrame.
            attributes = convertAttributes({
                    ConfigWindow.X: x,
                    ConfigWindow.Y: y,
                    ConfigWindow.Width: width,
                    ConfigWindow.Height: height,
                    ConfigWindow.StackMode: StackMode.Above
                    })
            xpybutil.conn.core.ConfigureWindow(frame.frameWindowID, *attributes)
            x += width

        xpybutil.conn.flush()

    def onSelectionRequest(self, event):
        logger.debug("onSelectionRequest:\n  %s", '\n  '.join(map(repr, event.__dict__.items())))
        mask = EventMask.NoEvent
        replyEvent = SelectionNotifyEvent.build()
        xpybutil.event.send_event(event.requestor, mask, replyEvent)
        event.SendEvent(false, event.requestor, EventMask.NoEvent, replyEvent)

    def onMapRequest(self, event):
        logger.debug("onMapRequest: %r", event.window)

        #TODO: Needed?
        #try:
        #    attribs = xpybutil.conn.GetWindowAttributes(event.window).reply()
        #except:
        #    logger.exception("onMapRequest: Error getting window attributes for window %r!", event.window)
        #    return
        #if attribs.override_redirect:
        #    return

        self.manageWindow(event.window)

        try:
            xpybutil.conn.core.MapWindowChecked(event.window).check()
        except:
            logger.exception("onMapRequest: Error mapping window %r!", event.window)
            return

    #TODO: Move into Frame.
    def onEnterNotify(self, event):
        if event.event in self.windows.values():
            self.focusWindow(event.event)

    def onUnmapNotify(self, event):
        self.unmanageWindow(event.window)
    # [end Move into Frame]

    def focusWindow(self, frame):
        logger.debug("onEnterNotify: Focusing %r.", frame.clientWindow)

        if self.focusedWindow is not None:
            self.focusedWindow.onLostFocus()

        self.focusedWindow = frame

        xpybutil.conn.core.SetInputFocus(InputFocus.PointerRoot, frame, xcb.CurrentTime)
        ewmh.set_active_window(frame.clientWindow)
        frame.onGainedFocus()

        xpybutil.conn.flush()

    def run(self):
        logger.info("Starting main event loop.")

        #xpybutil.event.main()
        #XXX: HACK to work around the fact that xpybutil.event will never send us MapNotify, even if we've subscribed
        # to SubstructureRedirect, and will never send us SelectionRequest when we own a selection. And yes, this is a
        # direct copy of xpybutil.event.main with some minor changes.
        try:
            while True:
                xpybutil.event.read(block=True)
                for e in xpybutil.event.queue():
                    w = None
                    if isinstance(e, MappingNotifyEvent):
                        w = None
                    elif isinstance(e, MapRequestEvent):
                        w = self.root
                    elif hasattr(e, 'window'):
                        w = e.window
                    elif hasattr(e, 'event'):
                        w = e.event
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

        except xcb.Exception:
            logger.exception("Error in main event loop!")
            sys.exit(1)
        #/HACK

        logger.info("Event loop terminated; shutting down.")
