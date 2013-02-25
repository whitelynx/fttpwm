# -*- coding: utf-8 -*-
"""FTTPWM: Floating window layout

Copyright (c) 2012-2013 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from .base import BaseLayout


class Floating(BaseLayout):
    """Doesn't arrange windows, leaving them where the user puts them.

    """
    def arrange(self, ws):
        frames = ws.viewableFrames

        # Ensure all frames are visible
        for frame in frames:
            frame.onShow()
