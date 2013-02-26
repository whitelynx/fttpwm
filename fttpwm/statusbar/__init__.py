"""FTTPWM: Status bar

Copyright (c) 2012-2013 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from collections import Mapping
from datetime import timedelta
import logging

from xcb.xproto import CW, ConfigureNotifyEvent

import xpybutil
import xpybutil.event
import xpybutil.ewmh as ewmh

import cairo

from ..settings import settings
from ..utils.time import StrftimeFormatter
from .. import singletons


UINT32_MAX = 2 ** 32

settings.setDefaults(
        enableStatusBar=False,
        statusBarContents=[
            'FTTPWM',
            ],
        statusBarLeftFormat=u'{wbcs}{workspacesBeforeCurrent} <{currentWorkspace}> {workspacesAfterCurrent}{wacs}',
        statusBarRightFormat='{isodatetime} ',
        #statusBarCenterFormat='FTTPWM',
        statusBarCenterFormat='',
        statusBarTitle='**statusbar**',
        )


class StatusBarFormatter(Mapping):
    def format(self, fmt):
        if callable(fmt):
            return fmt()

        else:
            # Create a new StrftimeFormatter so it gets `now` again.
            self.formatter = StrftimeFormatter()

            return self.formatter.vformat(fmt, [], self)

    @property
    def isodate(self):
        return self.formatter.now.date().isoformat()

    @property
    def isotime(self):
        return self.formatter.now.time().replace(microsecond=0).isoformat()

    @property
    def isodatetime(self):
        return self.formatter.now.replace(microsecond=0).isoformat(' ')

    @property
    def workspaces(self):
        return singletons.wm.workspaces

    @property
    def currentWorkspace(self):
        return singletons.wm.workspaces.current.name

    @property
    def workspacesBeforeCurrent(self):
        return singletons.wm.workspaces.namesBeforeCurrent

    @property
    def wbcs(self):
        return u'  ' if singletons.wm.workspaces.namesBeforeCurrent else u''  # Space if we're not on WS 1

    @property
    def workspacesAfterCurrent(self):
        return singletons.wm.workspaces.namesAfterCurrent

    @property
    def wacs(self):
        return u'  ' if singletons.wm.workspaces.namesAfterCurrent else u''  # Space if we're not on the last WS

    def __len__(self):
        return len(self.__dict__)

    def __iter__(self):
        return iter(self.__dict__)

    def __getitem__(self, key):
        return getattr(self, key)


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

        self.width, self.height = singletons.x.screenWidth, settings.theme.statusBar['height']
        self.x, self.y = 0, singletons.x.screenHeight - self.height

        self.formatter = StatusBarFormatter()

        # Create status bar window.
        self.windowAttributes = {
                CW.OverrideRedirect: 1,
                CW.BackPixel: singletons.x.black,
                }
        self.windowID, createWindowCookie = singletons.x.createWindow(
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
        self.surface = cairo.XCBSurface(xpybutil.conn, self.windowID, singletons.x.visual, self.width, self.height)
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

        singletons.eventloop.callEvery(timedelta(seconds=1), self.paint)
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
                singletons.x.depth, self.backPixmapID, self.windowID, self.width, self.height
                ))

        surface = cairo.XCBSurface(xpybutil.conn, self.backPixmapID, singletons.x.visual,
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

        self.leftText = self.formatter.format(settings.statusBarLeftFormat)
        self.rightText = self.formatter.format(settings.statusBarRightFormat)
        self.centerText = self.formatter.format(settings.statusBarCenterFormat)

        self.context.set_source(self.bgPattern)
        self.context.paint()

        settings.theme.paintStatusBar(self.context, self)

        self.surface.flush()
        xpybutil.conn.flush()

        return True
