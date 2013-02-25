# -*- coding: utf-8 -*-
"""FTTPWM: Simple tiling window layouts

Copyright (c) 2012-2013 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from .base import ListLayout, TilingLayout


class Columns(ListLayout, TilingLayout):
    """Arranges all frames on a workspace in columns, giving each window equal width and full height.

    """
    def startArrange(self, ws, frameCount):
        self.firstFrameX = ws.effectiveWorkAreaX + self.padding
        self.frameY = ws.effectiveWorkAreaY + self.padding
        self.frameWidth = (ws.effectiveWorkAreaWidth - self.padding) / frameCount - self.padding
        self.frameHeight = ws.effectiveWorkAreaHeight - 2 * self.padding
        self.frameXIncrement = (self.frameWidth + self.padding)

    def framePosition(self, index, frame, ws, frameCount):
        frameX = self.firstFrameX + index * self.frameXIncrement
        return (frameX, self.frameY, self.frameWidth, self.frameHeight)


class Rows(ListLayout, TilingLayout):
    """Arranges all frames on a workspace in rows, giving each window full width and equal height.

    """
    def startArrange(self, ws, frameCount):
        self.frameX = ws.effectiveWorkAreaX + self.padding
        self.firstFrameY = ws.effectiveWorkAreaY + self.padding
        self.frameWidth = ws.effectiveWorkAreaWidth - 2 * self.padding
        self.frameHeight = (ws.effectiveWorkAreaHeight - self.padding) / frameCount - self.padding
        self.frameYIncrement = (self.frameHeight + self.padding)

    def framePosition(self, index, frame, ws, frameCount):
        frameY = self.firstFrameY + index * self.frameYIncrement
        return (self.frameX, frameY, self.frameWidth, self.frameHeight)
