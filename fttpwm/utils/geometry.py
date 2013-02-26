# -*- coding: utf-8 -*-
"""FTTPWM: Geometry classes

Copyright (c) 2013 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""


class Vector(object):
    def __init__(self, x, y):
        self.x, self.y = x, y

    def __len__(self):
        return 2

    def __iter__(self):
        return iter((
                self.x, self.y
                ))

    def __add__(self, other):
        return Vector(*(s + o for s, o in zip(self, other)))

    __radd__ = __add__

    def __sub__(self, other):
        return Vector(*(s - o for s, o in zip(self, other)))

    def __rsub__(self, other):
        return Vector(*(o - s for s, o in zip(self, other)))


class Rect(object):
    def __init__(self, x, y, width, height):
        self.x, self.y, self.width, self.height = x, y, width, height

    def __len__(self):
        return 4

    def __iter__(self):
        return iter((
                self.x, self.y,
                self.width, self.height
                ))

    def asDict(self):
        return {
                'x': self.x, 'y': self.y,
                'width': self.width, 'height': self.height
                }

    @property
    def topLeft(self):
        return Vector(self.x, self.y)

    @property
    def topRight(self):
        return Vector(self.x + self.width, self.y)

    @property
    def bottomLeft(self):
        return Vector(self.x, self.y + self.height)

    @property
    def bottomRight(self):
        return Vector(self.x + self.width, self.y + self.height)

    @property
    def center(self):
        return Vector(self.x + self.width / 2, self.y + self.height / 2)

    @property
    def size(self):
        return Vector(self.width, self.height)

    def grow(self, growX, growY=None):
        if growY is None:
            growY = growX

        return Rect(
                self.x - growX / 2, self.y - growY / 2,
                self.width + growX, self.height + growY
                )

    def shrink(self, shrinkX, shrinkY=None):
        if shrinkY is None:
            shrinkY = shrinkX

        return self.grow(-shrinkX, -shrinkY)
