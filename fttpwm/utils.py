# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: Utility functions

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import datetime
import logging
import re
import string
import struct


logger = logging.getLogger("fttpwm.utils")


def loggerFor(cls):
    if not isinstance(cls, type):
        cls = type(cls)

    return logging.getLogger('{}.{}'.format(cls.__module__, cls.__name__))


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


class StrftimeFormatter(string.Formatter):
    """A class meant to hack the syntax of str.format() so you can do strftime formatting in a format string.

    Example:

        >>> from datetime import datetime
        >>> StrftimeFormatter().format("Hello, {name}! The current time is %Y-%m-%d %H:%M:%S", name="Dave")
        '2012-05-28 16:41:56'

    It also provides the 'now' field; if you like the ISO standard for representing datetimes, you can just use this:

        >>> StrftimeFormatter().format("{now}")
        '2012-05-28 16:43:41.828718'

    If you don't want the microseconds shown, use 'now_no_ms':

        >>> StrftimeFormatter().format("{now_no_ms}")
        '2012-05-28 16:46:12'

    """
    strftimeRE = re.compile(r'%[aAbBcdfHIjmMpSUwWxXyYzZ]')

    def __init__(self):
        self.now = datetime.datetime.now()
        self.now_no_ms = self.now.replace(microsecond=0)
        return super(StrftimeFormatter, self).__init__()

    def parse(self, format_string):
        format_string = self.strftimeRE.sub(r'{\g<0>}', format_string)
        return super(StrftimeFormatter, self).parse(format_string)

    def get_value(self, key, args, kwargs):
        if len(key) == 2 and key[0] == '%':
            if key[1] == '%':
                return '%'
            else:
                return kwargs.get('now', self.now).strftime(key)

        elif key == 'now':
            return kwargs.get('now', self.now)
        elif key == 'now_no_ms':
            return kwargs.get('now_no_ms', self.now_no_ms)

        return super(StrftimeFormatter, self).get_value(key, args, kwargs)
