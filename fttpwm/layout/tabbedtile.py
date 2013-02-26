# -*- coding: utf-8 -*-
"""FTTPWM: Tabbed tiling window layout

Copyright (c) 2012-2013 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from collections import defaultdict

import xpybutil

from .base import ListLayout, TilingLayout
from .tabbed import TabbedMaximized


# To store which pane a given frame is in:
#frame.setLayoutInfo(self, {
#        'pane': paneIndex
#        })

# To retrieve which pane a given frame is in:
#paneIndex = frame.getLayoutInfo(self).get('pane', float('inf'))


class TabbedColumns(ListLayout, TilingLayout):
    """Arranges frames on a workspace into tabbed columns, giving each column equal width and full height.

    """
    innerLayoutClass = TabbedMaximized

    def __init__(self, *args, **kwargs):
        self.subLayoutsByWorkspace = defaultdict(list)

        super(TabbedColumns, self).__init__(*args, **kwargs)

    def createInnerLayout(self, ws, before=None, subLayoutID=None, layoutClass=None):
        if before is None:
            before = len(self.subLayoutsByWorkspace[ws])

        layoutClass = layoutClass or self.innerLayoutClass

        layout = layoutClass(id=(subLayoutID or id(layout)))
        layout.parentInfoKey = self.layoutInfoKey

        self.subLayoutsByWorkspace[ws].insert(before, layout)
        self.storeLayoutInfo(ws)
        return layout

    def storeLayoutInfo(self, ws):
        ws.setLayoutInfo(self, {
                'subLayouts': [
                    {
                        'type': subLayout.layoutType,
                        'id': subLayout.id
                        }
                    for subLayout in self.subLayoutsByWorkspace[ws]
                    ]
                })

    def loadLayoutInfo(self, ws):
        layoutIDs = [subLayout.id for subLayout in self.subLayoutsByWorkspace[ws]]

        info = ws.getLayoutInfo(self)
        for idx, slDesc in enumerate(info['subLayouts']):
            if slDesc['id'] not in layoutIDs:
                self.createInnerLayout(ws, idx, slDesc['id'], slDesc['type'])

    #FIXME: From here down, this is probably mostly wrong.
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

    def startArrange(self, ws, frameCount):
        self.firstFrameX = ws.innerX + self.padding
        self.frameY = ws.innerY + self.padding
        self.frameWidth = (ws.innerWidth - self.padding) / frameCount - self.padding
        self.frameHeight = ws.innerHeight - 2 * self.padding
        self.frameXIncrement = (self.frameWidth + self.padding)

    def framePosition(self, index, frame, ws, frameCount):
        frameX = self.firstFrameX + index * self.frameXIncrement
        return (frameX, self.frameY, self.frameWidth, self.frameHeight)
