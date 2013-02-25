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
        self.firstFrameX = ws.innerX + self.padding
        self.frameY = ws.innerY + self.padding
        self.frameWidth = (ws.innerWidth - self.padding) / frameCount - self.padding
        self.frameHeight = ws.innerHeight - 2 * self.padding
        self.frameXIncrement = (self.frameWidth + self.padding)

    def framePosition(self, index, frame, ws, frameCount):
        frameX = self.firstFrameX + index * self.frameXIncrement
        return (frameX, self.frameY, self.frameWidth, self.frameHeight)


class Rows(ListLayout, TilingLayout):
    """Arranges all frames on a workspace in rows, giving each window full width and equal height.

    """
    def startArrange(self, ws, frameCount):
        self.frameX = ws.innerX + self.padding
        self.firstFrameY = ws.innerY + self.padding
        self.frameWidth = ws.innerWidth - 2 * self.padding
        self.frameHeight = (ws.innerHeight - self.padding) / frameCount - self.padding
        self.frameYIncrement = (self.frameHeight + self.padding)

    def framePosition(self, index, frame, ws, frameCount):
        frameY = self.firstFrameY + index * self.frameYIncrement
        return (self.frameX, frameY, self.frameWidth, self.frameHeight)
