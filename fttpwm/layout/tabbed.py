# -*- coding: utf-8 -*-
"""FTTPWM: Tabbed full-screen window layout

Copyright (c) 2012-2013 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from .base import ListLayout, TilingLayout


class TabbedMaximized(ListLayout, TilingLayout):
    """Shows the focused window maximized, and rolls all other windows into tabs.

    """
    def startArrange(self, ws, frameCount):
        self.frameX = ws.innerX + self.padding
        self.frameY = ws.innerY + self.padding
        self.frameWidth = ws.innerWidth - 2 * self.padding
        self.frameHeight = ws.innerHeight - 2 * self.padding

        if ws.focusedWindow is not None:
            ws.focusedWindow.onShow()

    def framePosition(self, index, frame, ws, frameCount):
        return (self.frameX, self.frameY, self.frameWidth, self.frameHeight)

    def onFramePositioned(self, index, frame, ws, frameCount):
        # Only show the currently-focused frame.
        if frame is not ws.focusedWindow:
            frame.hide()
