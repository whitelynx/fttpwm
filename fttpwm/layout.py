"""FTTPWM: Window layouts

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from abc import ABCMeta, abstractmethod
import logging
import math

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
    logger = logging.getLogger("fttpwm.layouts.Floating")

    def arrange(self, ws):
        frames = ws.viewableFrames

        # Ensure all frames are visible
        for frame in frames:
            frame.onShow()


class ListLayout(BaseLayout):
    """Base class for layouts which track all of their windows in a single sortable list.

    """
    def arrange(self, ws):
        frames = ws.viewableFrames
        frames.sort(key=lambda f: f.getLayoutInfo(self).get('index', float('inf')))
        frameCount = len(frames)

        self.logger.debug("arrange: Arranging frames: %r", frames)

        self.startArrange(ws, frameCount)

        for index, frame in enumerate(frames):
            geometry = self.framePosition(index, frame, ws, frameCount)
            self.logger.debug("Moving/resizing %r to %r.", frame, geometry)
            frame.moveResize(*geometry, flush=False)

            self.onFramePositioned(index, frame, ws, frameCount)

            # Update all frame indices to be consecutive integers.
            frame.setLayoutInfo(self, {'index': index})

        xpybutil.conn.flush()

    @abstractmethod
    def startArrange(self, ws, frameCount):
        pass

    @abstractmethod
    def framePosition(self, index, frame, ws, frameCount):
        pass

    def onFramePositioned(self, index, frame, ws, frameCount):
        # By default, ensure all frames are visible
        frame.onShow()

    def moveFrame(self, frame, n):
        """Move the frame forward or backward within its list of siblings by the given number of positions.

        """
        currentIndex = frame.getLayoutInfo(self).get('index', float('inf'))

        frame.setLayoutInfo(self, {
                'index': currentIndex + n + math.copysign(0.5, n)  # Add 0.5 to put it beyond the given sibling.
                })

        # Now, rearrange the window's workspace. (will convert all indices back to consecutive integers)
        frame.workspace.arrangeWindows()

    def focusSiblingFrame(self, frame, n):
        """Focus the frame `n` positions before (n < 0) or after (n > 0) the given one.

        """
        try:
            frames = frame.workspace.viewableFrames
        except ReferenceError:
            print frame
            print frame.workspace
            print frame.workspace.viewableFrames
        frames.sort(key=lambda f: f.getLayoutInfo(self).get('index', float('inf')))
        siblingIdx = (frames.index(frame) + n) % len(frames)
        frames[siblingIdx].focus()


class Columns(ListLayout):
    """Arranges all frames on a workspace in columns, giving each window equal width and full height.

    """
    logger = logging.getLogger("fttpwm.layouts.Columns")

    def __init__(self, padding=0):
        self.padding = padding

    def startArrange(self, ws, frameCount):
        self.firstFrameX = ws.effectiveWorkAreaX + self.padding
        self.frameY = ws.effectiveWorkAreaY + self.padding
        self.frameWidth = (ws.effectiveWorkAreaWidth - self.padding) / frameCount - self.padding
        self.frameHeight = ws.effectiveWorkAreaHeight - 2 * self.padding
        self.frameXIncrement = (self.frameWidth + self.padding)

    def framePosition(self, index, frame, ws, frameCount):
        frameX = self.firstFrameX + index * self.frameXIncrement
        return (frameX, self.frameY, self.frameWidth, self.frameHeight)


class Rows(ListLayout):
    """Arranges all frames on a workspace in rows, giving each window full width and equal height.

    """
    logger = logging.getLogger("fttpwm.layouts.Rows")

    def __init__(self, padding=0):
        self.padding = padding

    def startArrange(self, ws, frameCount):
        self.frameX = ws.effectiveWorkAreaX + self.padding
        self.firstFrameY = ws.effectiveWorkAreaY + self.padding
        self.frameWidth = ws.effectiveWorkAreaWidth - 2 * self.padding
        self.frameHeight = (ws.effectiveWorkAreaHeight - self.padding) / frameCount - self.padding
        self.frameYIncrement = (self.frameHeight + self.padding)

    def framePosition(self, index, frame, ws, frameCount):
        frameY = self.firstFrameY + index * self.frameYIncrement
        return (self.frameX, frameY, self.frameWidth, self.frameHeight)


class TabbedMaximized(ListLayout):
    """Shows the focused window maximized, and rolls all other windows into tabs.

    """
    logger = logging.getLogger("fttpwm.layouts.TabbedMaximized")

    def __init__(self, padding=0):
        self.padding = padding

    def startArrange(self, ws, frameCount):
        self.frameX = ws.effectiveWorkAreaX + self.padding
        self.frameY = ws.effectiveWorkAreaY + self.padding
        self.frameWidth = ws.effectiveWorkAreaWidth - 2 * self.padding
        self.frameHeight = ws.effectiveWorkAreaHeight - 2 * self.padding

        if ws.focusedWindow is not None:
            ws.focusedWindow.onShow()

    def framePosition(self, index, frame, ws, frameCount):
        return (self.frameX, self.frameY, self.frameWidth, self.frameHeight)

    def onFramePositioned(self, index, frame, ws, frameCount):
        # Only show the currently-focused frame.
        if frame is not ws.focusedWindow:
            frame.hide()
