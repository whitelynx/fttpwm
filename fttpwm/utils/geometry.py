# -*- coding: utf-8 -*-
"""FTTPWM: Geometry classes

Copyright (c) 2013 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from functools import wraps


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


def _defaultYToX(wrapped):
    @wraps(wrapped)
    def wrapper(self, x, y=None):
        if y is None:
            y = x

        return wrapped(self, x, y)

    return wrapper


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

    @_defaultYToX
    def grow(self, growX, growY=None):
        return Rect(
                self.x, self.y,
                self.width + growX, self.height + growY
                )

    @_defaultYToX
    def shrink(self, shrinkX, shrinkY=None):
        return self.grow(-shrinkX, -shrinkY)

    @_defaultYToX
    def growCentered(self, growX, growY=None):
        return self.grow(growX, growY).move(-growX / 2, -growY / 2)

    @_defaultYToX
    def shrinkCentered(self, shrinkX, shrinkY=None):
        return self.grow(-shrinkX, -shrinkY).move(shrinkX / 2, shrinkY / 2)

    def move(self, moveByX, moveByY):
        return Rect(
                self.x + moveByX, self.y + moveByY,
                self.width, self.height
                )
