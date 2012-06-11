"""FTTPWM: Status bar - base widget

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from abc import ABCMeta, abstractmethod
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
from ..icccm import ICCCMWindowState
from ..mouse import bindMouse
from ..signals import Signal
from ..settings import settings
from ..themes import Default, fonts
from ..utils import convertAttributes, StrftimeFormatter
from .. import singletons


class BaseWidget(object):
    __metaclass__ = ABCMeta

    def __init__(self, minSize=(16, 16), maxSize=(None, 16)):
        self.minSize = minSize
        self.maxSize = maxSize
        self._statusBar = None
        self.surface = None

    @property
    def statusBar(self):
        return self._statusBar

    @statusBar.setter
    def statusBar(self, statusBar):
        self._statusBar = statusBar

        if self.surface is not None:
            self.surface.finish()

        self.surface = cairo.XCBSurface(xpybutil.conn, statusBar.windowID, singletons.x.visual,
                statusBar.width, statusBar.height)
        self.context = cairo.Context(self.surface)
        self.context.set_operator(cairo.OPERATOR_OVER)

    @abstractmethod
    def paint(self, target, x, y, width, height):
        pass


class PixmapBackedWidget(BaseWidget):
    def __init__(self, *args, **kwargs):
        super(PixmapBackedWidget, self).__init__(*args, **kwargs)

        self.pixmapID = None

        self.logger = logging.getLogger('.'.join(__name__, type(self).__name__))

    @abstractmethod
    def paintPixmap(self):
        pass

    def createPixmap(self, x, y, width, height):
        cookies = list()
        self.pixmapID = xpybutil.conn.generate_id()

        cookies.append(xpybutil.conn.core.CreatePixmapChecked(
                singletons.x.depth, self.pixmapID, self.statusBar.windowID, width, height
                ))

        # Set up Cairo.
        self.pixmapSurface = cairo.XCBSurface(xpybutil.conn, self.pixmapID, singletons.x.visual, self.width, self.height)
        self.pixmapContext = cairo.Context(self.pixmapSurface)
        self.pixmapContext.set_operator(cairo.OPERATOR_OVER)

        self.logger.trace("Painting status bar background...")
        settings.theme.paintStatusBarWidgetBackground(self.pixmapContext, self)
        self.logger.trace("Done painting status bar background.")

        xpybutil.conn.flush()

        cookies.append(xpybutil.conn.core.ChangeWindowAttributesChecked(self.windowID, *convertAttributes({
                CW.BackPixmap: self.pixmapID
                })))

    def paint(self, target, x, y, width, height):
        if not self.mapped:
            return

        if self.pixmapID is None:
            self.createPixmap(x, y, width, height)
            self.paintPixmap()

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

        # Clear the window to the background pixmap.
        xpybutil.conn.core.ClearAreaChecked(False, self.windowID, 0, 0, 0, 0).check()

        # Draw the status bar text.
        self.surface.mark_dirty()
        settings.theme.paintStatusBar(self.context, self)
        self.surface.flush()
        xpybutil.conn.flush()
