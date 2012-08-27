# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: D-Bus remote object proxy class

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from collections import defaultdict
import logging
from weakref import ref, WeakSet

from .. import singletons

from .interface import _BaseDBusInterface, _BaseInterfaceMemberInfo
from .utils import MethodWrapper


logger = logging.getLogger('fttpwm.dbus.remote')


class _RemoteObjectInterfaceProxy(object):
    """A proxy object that fetches object members just for the given interface.

    """
    def __init__(self, interface):
        self.interface = interface
        self.obj = None

    def __get__(self, instance, owner):
        self.obj = ref(instance)

    def __getattr__(self, name):
        return getattr(self.obj, name)[self.interface]


class _RemoteObjectMeta(type):
    """Metaclass for remote DBus proxy objects.

    Adds proxy objects for all interface members on the remote object.

    """
    def __new__(mcs, name, bases, dict_):
        # Track all implemented interface members.
        membersByInterface = defaultdict(dict)
        membersByDBusName = defaultdict(set)

        # Find all explicit instances of interface members.
        for memberName, member in dict_.iteritems():
            if isinstance(member, _BaseInterfaceMemberInfo):
                membersByInterface[member.dbus_interface][memberName] = member
                membersByDBusName[member.dbus_name].add(member)

        # Find all instantiated interfaces.
        for shortName, interface in list(dict_.items()):
            if isinstance(interface, type) and issubclass(interface, _BaseDBusInterface):
                # Ensure that we have a dictionary entry for each interface.
                membersByInterface[interface].update({})

                # Replace each interface with a proxy object that fetches object members just for that interface.
                dict_[shortName] = _RemoteObjectInterfaceProxy(interface)

        # Instantiate all interface members that don't have explicit instances already.
        for interface in membersByInterface.keys():
            for method in interface._DBusInterface_getMethods():
                inst = method()
                membersByInterface[method.dbus_interface][memberName] = inst
                membersByDBusName[method.dbus_name].add(inst)

            for signal in interface._DBusInterface_getSignals():
                inst = signal()
                membersByInterface[signal.dbus_interface][memberName] = inst
                membersByDBusName[signal.dbus_name].add(inst)

            #TODO: Properties!

        dict_['_dbus_interfaces'] = WeakSet(membersByInterface.keys())

        for memberName, members in membersByDBusName.items():
            dict_[memberName] = MethodWrapper(memberName, members)

        returned = type.__new__(mcs, name, bases, dict_)
        return returned


class RemoteObject(object):
    """The base class for proxy objects which allow interacting with remote DBus objects.


    Brief Example
    -------------

        class RemoteExample(RemoteObject):
            sample = SampleInterface

        remoteObj = RemoteExample(
                '/com/example/Sample',  # The remote object's path
                'com.example.Sample',   # The bus name of the connection this remote object lives on (optional)
                bus=bus                 # Our connection to the bus
                )

        # Calling a method on a remote proxy object:
        remoteObj.StringifyVariant("Some value!")

        # Or, specifying full types:
        remoteObj.StringifyVariant(fttpwm.dbus.proto.types.Variant(fttpwm.dbus.proto.types.String, "Some value!"))

        # If more than one interface on the remote object defines the same method, specify which interface to use:
        remoteObj.StringifyVariant[SampleInterface]("Some value!")

        # Another way to specify the interface:
        remoteObj.sample.StringifyVariant("Some value!")


    Usage
    -----

    In order to make a new proxy object, you must first define a subclass which contains the needed interfaces as
    member variables, and then instantiate it:

        class ExampleRemoteObject(RemoteObject):
            sample = SampleInterface
            peer = PeerInterface

        remoteObj = ExampleRemoteObject(
                '/com/example/Sample',  # The remote object's path
                'com.example.Sample',   # The bus name of the connection this remote object lives on (optional)
                bus=bus                 # Our connection to the bus (optional; defaults to the session bus)
                )


    Accessing Object Members
    ------------------------

    Instances of each `RemoteObject` subclass will have members corresponding to all members of the interfaces
    contained in the class. Those members are instances of a custom class which allows you to specify the interface to
    look for members of, allowing you to access members of different interfaces in the remote object which share the
    same name. If only one interface on a remote object includes a member with a given name, you may work with that
    member using its name as usual:

        cb = remoteObj.StringifyVariant(33)

    However, if two or more interfaces on the remote object contain members with the same name, you MUST specify the
    interface (or fully-qualified name of the interface) whose member you wish to access:

        cb = remoteObj.Ping[PeerInterface]()
        cb = remoteObj.Ping["org.freedesktop.DBus.PeerInterface"]()

    As an alternative, you may instead use the members of the interface instances defined on the `RemoteObject`
    subclass:

        cb = remoteObj.peer.Ping()


    Calling Methods
    ---------------

    Aside from the above, calling a method on a remote object is almost identical to normal Python, with the exception
    of keyword arguments.  Passing method arguments as keyword arguments is not yet supported (FIXME!), and there is a
    special keyword argument: `dbus_destination`. This specifies which connection to send the method call to. If you
    are using a `RemoteObject` subclass instance with a message bus (as opposed to a direct connection), you MUST
    either specify the destination connection name when instantiating the object, or specify it as the
    `dbus_destination` keyword argument when calling any method on the remote object:

        cb = remoteObj.StringifyVariant(
                "foo bar fez",
                dbus_destination="com.example.some.known.connection.name"
                )

    Callbacks
    ---------

    Method calls return a new `fttpwm.dbus.connection.Callbacks` object bound to the method call request; you can
    assign your own functions to its `onReturn` and `onError` properties in order to handle return values and errors.
    They are not `fttpwm.signals.Signal` instances yet, because of the desire to avoid race conditions by allowing
    callbacks to be called immediately if they are assigned after the return or error event has already occurred.

    #FIXME: It'd be nice if the callback handlers at least used the same interface as `Signal`.


    Signals
    -------

    Signals on remote objects are represented by `fttpwm.signals.Signal` instances.

    #TODO: Flesh this out more?


    Properties
    ----------

    #TODO: Describe properties on remote objects!

    """
    __metaclass__ = _RemoteObjectMeta

    def __init__(self, object_path, destination=None, bus=None):
        self.dbus_path = object_path
        self.dbus_destination = destination

        if bus is None:
            bus = singletons.dbusSessionBus
        self.dbus_bus = bus

    #FIXME: Finish implementation!


def test():
    from .interface import _createSampleInterface

    SampleInterface = _createSampleInterface()

    class RemoteExample(RemoteObject):
        sample = SampleInterface

    print(unicode(RemoteExample), repr(RemoteExample), dir(RemoteExample))
    print(RemoteExample.__doc__)
    print(RemoteExample._dbus_interfaces)

    remoteObj = RemoteExample(
            '/com/example/Sample',      # The remote object's path
            'com.example.Sample'        # The bus name of the connection this remote object lives on (optional)
            )

    print(unicode(remoteObj), repr(remoteObj), dir(remoteObj))
    print(remoteObj.__doc__)
    print(unicode(remoteObj.LastInputChanged), repr(remoteObj.LastInputChanged), dir(remoteObj.LastInputChanged))
    print(remoteObj.LastInputChanged.__doc__)
    print(unicode(remoteObj.GetLastInput), repr(remoteObj.GetLastInput), dir(remoteObj.GetLastInput))
    print(remoteObj.GetLastInput.__doc__)
