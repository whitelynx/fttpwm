# -*- coding: utf-8 -*-
"""FTTPWM: Base window layout classes

Copyright (c) 2012-2013 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from abc import ABCMeta, abstractmethod
import importlib
import math

import xpybutil

from ..utils import between, loggerFor


class BaseLayout(object):
    """The base class for all layouts; cannot be used directly.

    """
    __metaclass__ = ABCMeta

    def __init__(self, id=''):
        self.logger = loggerFor(self)
        self.parentInfoKey = ''
        self.id = id

    @property
    def layoutType(self):
        return '{}.{}'.format(type(self).__module__, type(self).__name__)

    @staticmethod
    def loadLayoutType(layoutType):
        module, cls = layoutType.rsplit('.', 1)
        return getattr(importlib.import_module(module), cls)

    @abstractmethod
    def arrange(self, workspace):
        pass

    def onFocusChanged(self, prevFrame, curFrame):
        pass

    @property
    def layoutInfoKey(self):
        cls = type(self)
        return '{}/{}.{}.{}'.format(self.parentInfoKey, cls.__module__, cls.__name__, self.id)

    def tabs(self, frame):
        return None


class TilingLayout(BaseLayout):
    def __init__(self, padding=0, *args, **kwargs):
        self.padding = padding

        super(TilingLayout, self).__init__(*args, **kwargs)


class ListLayout(BaseLayout):
    """Base class for layouts which track all of their windows in a single sortable list.

    """
    def arrange(self, ws):
        frames = self.sortedFrames(ws)
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
        frame._doShow()

    def sortedFrames(self, ws):
        return sorted(ws.viewableFrames, key=lambda frame: frame.getLayoutInfo(self).get('index', float('inf')))

    def moveFrame(self, frame, n):
        """Move the frame forward or backward within its list of siblings by the given number of positions.

        """
        currentPos = frame.getLayoutInfo(self).get('index', float('inf'))
        targetPos = currentPos + n

        frame.setLayoutInfo(self, {
                'index': targetPos
                })

        # Shift each sibling between the original and new positions by +1 or -1, to make room.
        shiftSiblingsBy = -int(math.copysign(1, n))

        self.logger.debug("Moving frame %r from position %r to %r; shifting siblings by %r.",
                frame, currentPos, targetPos, shiftSiblingsBy)

        for sibling in frame.workspace.viewableFrames:
            if sibling != frame:
                siblingPos = sibling.getLayoutInfo(self).get('index', float('inf'))

                if between(siblingPos, currentPos, targetPos) or siblingPos == targetPos:
                    self.logger.debug("Sibling frame %r (index %r) is in the range to be moved.", sibling, siblingPos)
                    sibling.setLayoutInfo(self, {
                            'index': siblingPos + shiftSiblingsBy
                            })
                else:
                    self.logger.debug("Sibling frame %r (index %r) is not in the range to be moved.",
                            sibling, siblingPos)

        # Now, rearrange the window's workspace. (will convert all indices back to consecutive integers)
        frame.workspace.arrangeWindows()

    def focusSiblingFrame(self, frame, n):
        """Focus the frame `n` positions before (n < 0) or after (n > 0) the given one.

        """
        frames = self.sortedFrames(frame.workspace)
        siblingIdx = (frames.index(frame) + n) % len(frames)
        frames[siblingIdx].focus()
