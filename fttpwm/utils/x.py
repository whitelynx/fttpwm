# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: X11 utility functions

Copyright (c) 2012-2013 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import struct


def convertAttributes(attributes):
    attribMask = 0
    attribValues = list()

    # Values must be sorted by CW enum value, ascending.
    # Luckily, the tuples we get from dict.iteritems will automatically sort correctly.
    for attrib, value in sorted(attributes.iteritems()):
        attribMask |= attrib
        attribValues.append(value)

    return attribMask, attribValues


def findCurrentVisual(screen, desiredDepth, visualID):
    """Find the VISUALTYPE object for our current visual.

    This is needed for initializing a Cairo XCBSurface.

    """
    for depth in screen.allowed_depths:
        if depth.depth == desiredDepth:
            for visual in depth.visuals:
                if visual.visual_id == visualID:
                    return visual


def signedToUnsigned16(signed):
    # Pack as a signed int, then unpack that as unsigned.
    return struct.unpack('!I', struct.pack('!i', signed))[0]
