"""FTTPWM: Status bar

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from datetime import datetime, timedelta
import logging

import xcb
from xcb.xproto import CW, ConfigWindow, StackMode, ConfigureNotifyEvent

import xpybutil
import xpybutil.event
import xpybutil.ewmh as ewmh
import xpybutil.icccm as icccm
from xpybutil.util import get_atom as atom

import cairo

from ..bindings.layout import Floating as FloatingBindings
from ..ewmh import EWMHAction, EWMHWindowState
from ..mouse import bindMouse
from ..signals import Signal
from ..settings import settings
from ..themes import Default, fonts
from ..utils import convertAttributes, StrftimeFormatter
from .. import singletons


UINT32_MAX = 2 ** 32

settings.setDefaults(
        enableStatusBar=False,
        statusBarLeftFormat=lambda:
            u'{wbcs}{workspacesBeforeCurrent} <{currentWorkspace}> {workspacesAfterCurrent}{wacs}'.format(
                currentWorkspace=singletons.wm.workspaces.current.name,
                workspacesBeforeCurrent=singletons.wm.workspaces.namesBeforeCurrent,
                wbcs=u'  ' if singletons.wm.workspaces.namesBeforeCurrent else u'',  # Spacing for if we're on WS 1
                workspacesAfterCurrent=singletons.wm.workspaces.namesAfterCurrent,
                wacs=u'  ' if singletons.wm.workspaces.namesAfterCurrent else u'',  # Spacing for if we're on the last
                ),
        statusBarRightFormat='{isodatetime} ',
        #statusBarCenterFormat='FTTPWM',
        statusBarCenterFormat='',
        statusBarTitle='**statusbar**',
        )


class StatusBar(object):
    @classmethod
    def startIfConfigured(cls):
        if settings.enableStatusBar:
            return cls()

    def __init__(self):
        self.windowID = xpybutil.conn.generate_id()
        self.backPixmapID = None

        self.logger = logging.getLogger("fttpwm.statusbar.{}".format(self.windowID))
        self.logger.info("Setting up status bar.")

        self.width, self.height = singletons.wm.screenWidth, settings.theme.statusBar['height']
        self.x, self.y = 0, singletons.wm.screenHeight - self.height

        # Create status bar window.
        self.windowAttributes = {
                CW.OverrideRedirect: 1,
                CW.BackPixel: singletons.wm.black,
                }
        self.windowID, createWindowCookie = singletons.wm.createWindow(
                self.x, self.y, self.width, self.height,
                attributes=self.windowAttributes, windowID=self.windowID, checked=True
                )
        ewmh.set_wm_name(self.windowID, settings.statusBarTitle)

        setWMStrutPartialCookie = ewmh.set_wm_strut_partial_checked(
                self.windowID,
                0, 0, 0, self.height,  # left, right, top, bottom,
                0, 0,                  # left_start_y, left_end_y
                0, 0,                  # right_start_y, right_end_y,
                0, 0,                  # top_start_x, top_end_x,
                0, self.width          # bottom_start_x, bottom_end_x
                )

        # Set up Cairo.
        self.surface = cairo.XCBSurface(xpybutil.conn, self.windowID, singletons.wm.visual, self.width, self.height)
        self.context = cairo.Context(self.surface)
        self.context.set_operator(cairo.OPERATOR_OVER)

        self.subscribeToEvents()

        xpybutil.conn.flush()

        createWindowCookie.check()
        setWMStrutPartialCookie.check()

        self.mapped = False
        try:
            xpybutil.conn.core.MapWindowChecked(self.windowID).check()
        except:
            self.logger.exception("Error mapping!")

        singletons.wm.callEvery(timedelta(seconds=1), self.paint)
        singletons.wm.workspaces.currentChanged.connect(self.paint)

    def subscribeToEvents(self):
        self.logger.info("Subscribing to events.")

        # Frame window events
        xpybutil.event.connect('ConfigureNotify', self.windowID, self.onConfigureNotify)
        xpybutil.event.connect('Expose', self.windowID, self.onExpose)
        xpybutil.event.connect('MapNotify', self.windowID, self.onMapNotify)
        xpybutil.event.connect('UnmapNotify', self.windowID, self.onUnmapNotify)

        xpybutil.window.listen(self.windowID, 'ButtonPress', 'Exposure', 'PropertyChange', 'StructureNotify')

    ## X events ####
    def onConfigureNotify(self, event):
        # If there's any other ConfigureNotify events for this window in the queue, ignore this one.
        xpybutil.event.read(block=False)
        for ev in xpybutil.event.peek():
            if isinstance(ev, ConfigureNotifyEvent) and ev.window == self.windowID:
                return

        if (self.x, self.y) != (event.x, event.y):
            self.logger.trace("onConfigureNotify: Window position changed to %r.", (event.x, event.y))
            self.x, self.y = event.x, event.y

        if (self.width, self.height) != (event.width, event.height):
            self.logger.trace("onConfigureNotify: Window size changed to %r.", (event.width, event.height))

            # Window size changed; resize surface and redraw.
            self.surface.set_size(event.width, event.height)
            self.width, self.height = event.width, event.height

            # Ditch old background pixmap so it's regenerated
            xpybutil.conn.core.FreePixmap(self.backPixmapID)
            self.backPixmapID = None

            self.paint()

    def onExpose(self, event):
        # A count of 0 denotes the last Expose event in a series of contiguous Expose events; this check lets us
        # collapse such series into a single call to paint() so we don't get extraneous redraws.
        if event.count == 0:
            self.paint()

    def onMapNotify(self, event):
        self.mapped = True
        self.paint()

    def onUnmapNotify(self, event):
        self.mapped = False

    def paintBackground(self):
        cookies = list()
        self.backPixmapID = xpybutil.conn.generate_id()

        cookies.append(xpybutil.conn.core.CreatePixmapChecked(
                singletons.wm.depth, self.backPixmapID, self.windowID, self.width, self.height
                ))

        surface = cairo.XCBSurface(xpybutil.conn, self.backPixmapID, singletons.wm.visual,
                self.width, self.height)
        context = cairo.Context(surface)
        context.set_operator(cairo.OPERATOR_OVER)

        self.logger.trace("Painting status bar background...")
        settings.theme.paintStatusBarBackground(context, self)
        self.logger.trace("Done painting status bar background.")

        surface.flush()
        self.bgPattern = cairo.SurfacePattern(surface)

        xpybutil.conn.flush()
        for cookie in cookies:
            cookie.check()

    def paint(self):
        if not self.mapped:
            return

        if self.backPixmapID is None:
            self.paintBackground()

        formatter = StrftimeFormatter()
        now = formatter.now
        kwargs = {
                'isodate': now.date().isoformat(),
                'isotime': now.time().replace(microsecond=0).isoformat(),
                'isodatetime': now.replace(microsecond=0).isoformat(' '),
                'workspaces': singletons.wm.workspaces,
                }

        def doText(fmt):
            if callable(fmt):
                return fmt()
            else:
                return formatter.format(fmt, **kwargs)

        self.leftText = doText(settings.statusBarLeftFormat)
        self.rightText = doText(settings.statusBarRightFormat)
        self.centerText = doText(settings.statusBarCenterFormat)

        self.context.set_source(self.bgPattern)
        self.context.paint()

        settings.theme.paintStatusBar(self.context, self)

        self.surface.flush()
        xpybutil.conn.flush()
