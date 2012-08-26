# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: D-Bus Introspectable interface

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import logging

from ..interface import DBusInterface, Method


logger = logging.getLogger("fttpwm.dbus.interfaces.introspectable")


class Introspectable(DBusInterface('org.freedesktop.DBus.Introspectable')):
    """Represents an object which may be inspected by other peers on the bus.

    """
    @Method(outSig='s')
    def Introspect(self):
        """Returns an XML description of the object, including its interfaces (with signals and methods), objects below
        it in the object path tree, and its properties.

        """
