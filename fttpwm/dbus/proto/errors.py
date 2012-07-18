# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: D-Bus exception types

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

NOTE: This implementation ONLY supports UNIX domain sockets currently. This will most likely be extended in the future,
but for now it limits what you can connect to.

"""


class DBusError(Exception):
    pass


class MessageParseError(DBusError):
    pass


class AuthenticationError(DBusError):
    pass


class MethodCallError(DBusError):
    pass


class NotEnoughData(DBusError):
    pass
