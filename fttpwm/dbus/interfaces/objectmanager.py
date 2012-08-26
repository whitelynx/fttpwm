# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: D-Bus ObjectManager interface

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import logging

from ..interface import DBusInterface, Method, Signal


logger = logging.getLogger("fttpwm.dbus.interfaces.objectmanager")


class ObjectManager(DBusInterface('org.freedesktop.DBus.ObjectManager')):
    """An API can optionally make use of this interface for one or more sub-trees of objects. The root of each sub-tree
    implements this interface so other applications can get all objects, interfaces and properties in a single method
    call. It is appropriate to use this interface if users of the tree of objects are expected to be interested in all
    interfaces of all objects in the tree; a more granular API should be used if users of the objects are expected to
    be interested in a small subset of the objects, a small subset of their interfaces, or both.

    Applications SHOULD NOT export objects that are children of an object (directly or otherwise) implementing this
    interface but which are not returned in the reply from the GetManagedObjects() method of this interface on the
    given object.

    The intent of the ObjectManager interface is to make it easy to write a robust client implementation. The trivial
    client implementation only needs to make two method calls:

        class RemoteObjectManager(fttpwm.dbus.remote.RemoteObject):
            objectManager = fttpwm.dbus.interfaces.ObjectManager()

        exampleApp = RemoteObjectManager(bus, '/org/example/App', 'org.example.App')

        bus.AddMatch("type='signal',name='org.example.App',path_namespace='/org/example/App'")
        objects = exampleApp.GetManagedObjects()

    on the message bus and the remote application's ObjectManager, respectively. Whenever a new remote object is
    created (or an existing object gains a new interface), the InterfacesAdded signal is emitted, and since this signal
    contains all properties for the interfaces, no calls to the org.freedesktop.Properties interface on the remote
    object are needed. Additionally, since the initial AddMatch() rule already includes signal messages from the newly
    created child object, no new AddMatch() call is needed.

    """
    @Method(outSig='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        """Get all objects and properties managed by this ObjectManager.

        The return value of this method is a dict whose keys are object paths. All returned object paths are children
        of the object path implementing this interface, i.e. their object paths start with the ObjectManager's object
        path plus '/'.

        Each value is a dict whose keys are interfaces names. Each value in this inner dict is the same dict that would
        be returned by the org.freedesktop.DBus.Properties.GetAll() method for that combination of object path and
        interface. If an interface has no properties, the empty dict is returned.

        """

    @Signal(sig='oa{sa{sv}}')
    def InterfacesAdded(self, objectPath, interfacesAndProperties):
        """Emitted when either a new object is added or when an existing object gains one or more interfaces.

        The second parameter is a dict of the interfaces and properties that were added to the given object path.

        """

    @Signal(sig='oas')
    def InterfacesRemoved(objectPath, interfaces):
        """Emitted whenever an object is removed or it loses one or more interfaces.

        The second parameter is an array of the interfaces that were removed from the given object path.

        """
