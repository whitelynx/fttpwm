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
import xpybutil.event as event
import xpybutil.ewmh as ewmh
from xpybutil.util import get_atom as atom
import xpybutil.window

from .settings import settings
from .utils import convertAttributes


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


class EWMHAction(object):
    Move = atom('_NET_WM_ACTION_MOVE')
    Resize = atom('_NET_WM_ACTION_RESIZE')
    Minimize = atom('_NET_WM_ACTION_MINIMIZE')
    Shade = atom('_NET_WM_ACTION_SHADE')
    Stick = atom('_NET_WM_ACTION_STICK')
    MaximizeHorz = atom('_NET_WM_ACTION_MAXIMIZE_HORZ')
    MaximizeVert = atom('_NET_WM_ACTION_MAXIMIZE_VERT')
    Fullscreen = atom('_NET_WM_ACTION_FULLSCREEN')
    ChangeDesktop = atom('_NET_WM_ACTION_CHANGE_DESKTOP')
    Close = atom('_NET_WM_ACTION_CLOSE')


class EWMHWindowState(object):
    Modal = atom('_NET_WM_STATE_MODAL')
    Sticky = atom('_NET_WM_STATE_STICKY')
    MaximizedVert = atom('_NET_WM_STATE_MAXIMIZED_VERT')
    MaximizedHorz = atom('_NET_WM_STATE_MAXIMIZED_HORZ')
    Shaded = atom('_NET_WM_STATE_SHADED')
    SkipTaskbar = atom('_NET_WM_STATE_SKIP_TASKBAR')
    SkipPager = atom('_NET_WM_STATE_SKIP_PAGER')
    Hidden = atom('_NET_WM_STATE_HIDDEN')
    Fullscreen = atom('_NET_WM_STATE_FULLSCREEN')
    Above = atom('_NET_WM_STATE_ABOVE')
    Below = atom('_NET_WM_STATE_BELOW')
    DemandsAttention = atom('_NET_WM_STATE_DEMANDS_ATTENTION')


class EWMHWindowType(object):
    Desktop = atom('_NET_WM_WINDOW_TYPE_DESKTOP')
    Dock = atom('_NET_WM_WINDOW_TYPE_DOCK')
    Toolbar = atom('_NET_WM_WINDOW_TYPE_TOOLBAR')
    Menu = atom('_NET_WM_WINDOW_TYPE_MENU')
    Utility = atom('_NET_WM_WINDOW_TYPE_UTILITY')
    Splash = atom('_NET_WM_WINDOW_TYPE_SPLASH')
    Dialog = atom('_NET_WM_WINDOW_TYPE_DIALOG')
    Normal = atom('_NET_WM_WINDOW_TYPE_NORMAL')


class Color(object):
    @staticmethod
    def float(*components):
        return map(lambda x: int(x * 2 ** 16), components)


class WM(object):
    def __init__(self):
        self.setup = xpybutil.conn.get_setup()
        self.screen = self.setup.roots[xpybutil.conn.pref_screen]
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

        self.windows = list()
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

        pid = os.getpid()
        logger.debug(
                "Setting up EWMH _NET_SUPPORTING_WM child window. (ID=%r, _NET_WM_PID=%r, _NET_WM_NAME=%r, "
                "_NET_SUPPORTING_WM_CHECK=%r)",
                self.ewmhChildWindow, pid, 'FTTPWM', self.ewmhChildWindow
                )
        ewmh.set_supporting_wm_check(self.ewmhChildWindow, self.ewmhChildWindow)
        ewmh.set_wm_name(self.ewmhChildWindow, 'FTTPWM')
        try:
            ewmh.set_wm_pid(self.ewmhChildWindow, pid)
        except OverflowError:
            #XXX: HACK to work around broken code in xpybutil.ewmh:
            packed = struct.pack('I', pid)
            xpybutil.conn.core.ChangeProperty(PropMode.Replace, self.ewmhChildWindow, atom('_NET_WM_PID'),
                    Atom.CARDINAL, 32, 1, packed)
            #/HACK

        self.setWMProps()
        self.setDesktopProps()

        logger.debug("startManaging: Subscribing to events.")

        xpybutil.window.listen(xpybutil.root, 'EnterWindow', 'LeaveWindow', 'PropertyChange',
                'SubstructureRedirect', 'SubstructureNotify', 'StructureNotify')
                # It might make sense to do this, but if we update our frames when we set the focus, it'll be faster.
                #'EventMask.FocusChange')

        logger.debug("startManaging: Reticulating splines.")

        event.connect('EnterNotify', self.root, self.onEnterNotify)
        event.connect('MapRequest', self.root, self.onMapRequest)

    def setWMProps(self):
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

    def manageWindow(self, window):
        logger.debug("Managing window %r...", window)

        cookies = []
        cookies.append(xpybutil.conn.core.ChangeSaveSetChecked(SetMode.Insert, window))

        #TODO: Move into Frame.
        xpybutil.window.listen(window, 'EnterWindow')  # 'FocusChange', 'PropertyChange', 'StructureNotify')
        event.connect('EnterNotify', window, self.onEnterNotify)
        event.connect('UnmapNotify', window, self.onUnmapNotify)

        ewmh.set_frame_extents(window, 0, 0, 0, 0)
        #ewmh.set_frame_extents(window, left, right, top, bottom)
        #ewmh.set_wm_window_opacity(frame, opacity)
        #title = ewmh.get_wm_name(window).reply() or icccm.get_wm_name(window).reply()
        ewmh.set_wm_state(window, [EWMHWindowState.MaximizedVert])
        ewmh.set_wm_allowed_actions(window, [
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
        #if atom('_NET_WM_PING') in icccm.get_wm_protocols(window).reply():
        #    self.startPing()
        # [end Move into Frame]

        #FIXME: We should pay attention to the _NET_WM_DESKTOP value if initially set by the client, and try to put the
        # window on that desktop. If it is not set, or the specified desktop doesn't exist, then we should set it.
        #ewmh.get_wm_desktop(window)
        ewmh.set_wm_desktop(window, 0)

        self.windows.append(window)
        ewmh.set_client_list(self.windows)
        self.rearrangeWindows()

    def unmanageWindow(self, window):
        if window not in self.windows:
            logger.warn("unmanageWindow: Window %r is not in our list of clients! Ignoring.", window)
            return

        logger.debug("Unmanaging window %r...", window)

        #TODO: Move into Frame.
        # Stop handling events from this window.
        event.disconnect('EnterNotify', window)
        event.disconnect('UnmapNotify', window)
        # [end Move into Frame]

        self.windows.remove(window)
        ewmh.set_client_list(self.windows)
        self.rearrangeWindows()

    def rearrangeWindows(self):
        if len(self.windows) == 0:
            return

        x = 0
        y = 0
        width = self.desktopWidth / len(self.windows)
        height = self.desktopHeight

        for window in self.windows:
            xpybutil.conn.core.ConfigureWindow(window, *convertAttributes({
                    ConfigWindow.X: x,
                    ConfigWindow.Y: y,
                    ConfigWindow.Width: width,
                    ConfigWindow.Height: height,
                    ConfigWindow.BorderWidth: 2 if window == self.focusedWindow else 0,
                    ConfigWindow.StackMode: StackMode.Above
                    }))
            x += width

        xpybutil.conn.flush()

    #def onPropertyChange(event):
    #    if util.get_atom_name(event.atom) == '_NET_ACTIVE_WINDOW':
    #        # Do something whenever the active window changes
    #        activeWindowID = ewmh.get_active_window().reply()

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
        if event.event in self.windows:
            self.focusWindow(event.event)

    def onUnmapNotify(self, event):
        self.unmanageWindow(event.window)
    # [end Move into Frame]

    def focusWindow(self, window):
        logger.debug("onEnterNotify: Focusing %r.", window)

        if self.focusedWindow is not None:
            xpybutil.conn.core.ConfigureWindow(self.focusedWindow, *convertAttributes({
                    ConfigWindow.BorderWidth: 0,
                    }))
            xpybutil.conn.core.ChangeWindowAttributes(self.focusedWindow, *convertAttributes({
                    CW.BorderPixel: self.unfocusedBorderColor
                    }))

        self.focusedWindow = window
        xpybutil.conn.core.SetInputFocus(InputFocus.PointerRoot, window, xcb.CurrentTime)
        xpybutil.conn.core.ConfigureWindow(self.focusedWindow, *convertAttributes({
                ConfigWindow.BorderWidth: 2,
                }))
        xpybutil.conn.core.ChangeWindowAttributes(self.focusedWindow, *convertAttributes({
                CW.BorderPixel: self.focusedBorderColor
                }))
        ewmh.set_active_window(window)
        xpybutil.conn.flush()

    def run(self):
        logger.info("Starting main event loop.")

        #event.main()
        #XXX: HACK to work around the fact that xpybutil.event will never send us MapNotify, even if we've subscribed
        # to SubstructureRedirect. And yes, this is a direct copy of event.main with some minor changes.
        try:
            while True:
                event.read(block=True)
                for e in event.queue():
                    w = None
                    if isinstance(e, MappingNotifyEvent):
                        w = None
                    elif isinstance(e, MapRequestEvent):
                        w = self.root
                    elif hasattr(e, 'window'):
                        w = e.window
                    elif hasattr(e, 'event'):
                        w = e.event
                    elif hasattr(e, 'requestor'):
                        w = e.requestor

                    key = (e.__class__, w)
                    for cb in getattr(event, '__callbacks').get(key, []):
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
