# -*- coding: utf-8 -*-
"""FTTPWM: Base theme class

Copyright (c) 2012-2013 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from abc import ABCMeta, abstractmethod
import logging

import xpybutil.ewmh as ewmh

from ..utils.geometry import Rect


logger = logging.getLogger("fttpwm.themes")


class BaseTheme(object):
    """The base class for all themes; cannot be used directly.

    """
    __metaclass__ = ABCMeta

    def __init__(self):
        self.currentFrame = None

    def __getitem__(self, key):
        return self.getFrameThemeValue(self.currentFrame, key)

    def getFrameThemeValues(self, frame, *keys):
        return self.getThemeValues(*keys, focused=frame.focused)

    def getFrameThemeValue(self, frame, key):
        return self.getThemeValue(key, focused=frame.focused)

    def getThemeValues(self, *keys, **state):
        return tuple(
                self.getThemeValue(key, **state)
                for key in keys
                )

    def getThemeValue(self, key, focused=False, statusBar=False):
        normalVal = self.normal.get(key)

        if focused:
            return self.focused.get(key, normalVal)

        if statusBar:
            return self.statusBar.get(key, normalVal)

        return normalVal

    def getFrameExtents(self, frame):
        """Retrieve the frame sizes appropriate for the given frame's window.

        Returns a tuple of frame sizes: (left, right, top, bottom)

        The ordering of the results is meant to follow the ordering of _NET_FRAME_EXTENTS from the EWMH specification.

        """
        return self.getFrameThemeValues(frame, 'borderWidth', 'borderWidth', 'titlebarHeight', 'borderWidth')

    def getClientGeometry(self, frame):
        """Retrieve the desired window geometry for the given frame's window, relative to the frame.

        Returns a Rect.

        """
        left, right, top, bottom = self.getFrameExtents(frame)
        return Rect(left, top, (frame.width - left - right), (frame.height - top - bottom))

    def apply(self, frame):
        ewmh.set_frame_extents(frame.clientWindowID, *self.getFrameExtents(frame))
        ewmh.set_wm_window_opacity(frame.frameWindowID, self.getFrameThemeValue(frame, 'opacity'))

    @abstractmethod
    def paintTab(self, ctx, frame, tabGeom=None):
        pass

    @abstractmethod
    def paintWindow(self, ctx, frame, titleGeom=None):
        pass

    @abstractmethod
    def paintStatusBarBackground(self, ctx, bar):
        pass

    @abstractmethod
    def paintStatusBar(self, ctx, bar):
        pass
