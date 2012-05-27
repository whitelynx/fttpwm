"""FTTPWM: Window layouts

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import logging
from abc import ABCMeta, abstractmethod

import xpybutil


class BaseLayout(object):
    """The base class for all layouts; cannot be used directly.

    """
    __metaclass__ = ABCMeta

    def __init__(self):
        pass

    @abstractmethod
    def arrange(self, workspace):
        pass


class Floating(BaseLayout):
    """Doesn't arrange windows, leaving them where the user puts them.

    """
    logger = logging.getLogger("fttpwm.layouts.Columns")

    #TODO: Move mouse-based move and resize here!

    def arrange(self, ws):
        pass


class Columns(BaseLayout):
    """Arranges all frames on a workspace in columns, giving each window equal width and full height.

    """
    logger = logging.getLogger("fttpwm.layouts.Columns")

    def __init__(self, padding=0):
        self.padding = padding

    def arrange(self, ws):
        frames = ws.viewableFrames

        self.logger.debug("arrange: Arranging frames: %r", frames)

        x = ws.effectiveWorkAreaX + self.padding
        y = ws.effectiveWorkAreaY + self.padding
        width = (ws.effectiveWorkAreaWidth - self.padding) / len(frames) - self.padding
        height = ws.effectiveWorkAreaHeight - 2 * self.padding

        for frame in frames:
            self.logger.debug("Moving/resizing %r to %r.", frame, (x, y, width, height))
            frame.moveResize(x, y, width, height, flush=False)
            x += width + self.padding

        xpybutil.conn.flush()


class Rows(BaseLayout):
    """Arranges all frames on a workspace in rows, giving each window full width and equal height.

    """
    logger = logging.getLogger("fttpwm.layouts.Rows")

    def __init__(self, padding=0):
        self.padding = padding

    def arrange(self, ws):
        frames = ws.viewableFrames

        self.logger.debug("arrange: Arranging frames: %r", frames)

        x = ws.effectiveWorkAreaX + self.padding
        y = ws.effectiveWorkAreaY + self.padding
        width = ws.effectiveWorkAreaWidth - 2 * self.padding
        height = (ws.effectiveWorkAreaHeight - self.padding) / len(frames) - self.padding

        for frame in frames:
            self.logger.debug("Moving/resizing %r to %r.", frame, (x, y, width, height))
            frame.moveResize(x, y, width, height, flush=False)
            y += height + self.padding

        xpybutil.conn.flush()
