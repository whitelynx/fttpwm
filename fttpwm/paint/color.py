# -*- coding: utf-8 -*-
"""FTTPWM: Color conversion

Copyright (c) 2012-2013 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import logging
import re


logger = logging.getLogger("fttpwm.paint.color")


class Color(object):
    stringFormats = [
            (lambda x: float(int(x, 16)) / 0xF,
                re.compile('#(?P<r>[0-9a-fA-F])(?P<g>[0-9a-fA-F])(?P<b>[0-9a-fA-F])(?P<a>[0-9a-fA-F])?$')),
            (lambda x: float(int(x, 16)) / 0xFF,
                re.compile('#(?P<r>[0-9a-fA-F]{2})(?P<g>[0-9a-fA-F]{2})(?P<b>[0-9a-fA-F]{2})(?P<a>[0-9a-fA-F]{2})?$')),
            (lambda x: float(int(x, 16)) / 0xFFFF,
                re.compile('#(?P<r>[0-9a-fA-F]{4})(?P<g>[0-9a-fA-F]{4})(?P<b>[0-9a-fA-F]{4})(?P<a>[0-9a-fA-F]{4})?$')),
            ]

    def __init__(self, string=None):
        self.r, self.g, self.b, self.a = 0, 0, 0, 1

        if string is not None:
            matched = False

            for conv, fmt in self.stringFormats:
                match = fmt.match(string)
                if match:
                    matched = True
                    self.r, self.g, self.b = map(conv, match.group('r', 'g', 'b'))
                    if match.group('a') is not None:
                        self.a = conv(match.group('a'))

            if not matched:
                logger.warn("Color: Couldn't parse color definition %r! Defaulting to opaque black.", string)

    def __iter__(self):
        return iter((self.r, self.g, self.b, self.a))

    @classmethod
    def rgb(cls, r, g, b):
        color = cls()
        color.r, color.g, color.b = r, g, b
        return color

    @classmethod
    def rgba(cls, r, g, b, a):
        color = cls()
        color.r, color.g, color.b, color.a = r, g, b, a
        return color
