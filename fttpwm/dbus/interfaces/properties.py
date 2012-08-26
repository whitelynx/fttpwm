# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: D-Bus Properties interface

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import logging

from ..interface import DBusInterface, Method, Signal


logger = logging.getLogger("fttpwm.dbus.interfaces.properties")


class Properties(DBusInterface('org.freedesktop.DBus.Properties')):
    """Many native APIs will have a concept of object properties or attributes. These can be exposed via this
    interface.

    """
    @Method(inSig='ss', outSig='v')
    def Get(self, interfaceName, propertyName):
        """Get the value of the given property on the given interface.

        """

    @Method(inSig='ssv')
    def Set(self, interfaceName, propertyName, value):
        """Set the value of the given property on the given interface.

        """

    @Method(inSig='s', outSig='a{sv}')
    def GetAll(self, interfaceName):
        """Get the value of all properties on the given interface.

        """

    @Signal(sig='sa{sv}as')
    def PropertiesChanged(self, interfaceName, changedProperties, invalidatedProperties):
        """Emitted whenever one or more properties change on an object.

        `changed_properties` is a dictionary containing the changed properties with the new values, and
        `invalidated_properties` is an array of properties that changed but the value is not conveyed.

        Whether the PropertiesChanged signal is supported can be determined by calling
        `org.freedesktop.DBus.Introspectable.Introspect`. Note that the signal may be supported for an object but it
        may differ whether and how it is used on a per-property basis (for e.g. performance or security reasons). Each
        property (or the parent interface) must be annotated `org.freedesktop.DBus.Property.EmitsChangedSignal` to
        convey this. (usually the default value `true` is sufficient, meaning that the annotation does not need to be
        used)

        """
