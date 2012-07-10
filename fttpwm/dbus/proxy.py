# -*- cod-ing: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: D-Bus method and signal proxy decorators

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

NOTE: This implementation ONLY supports UNIX domain sockets currently. This will most likely be extended in the future,
but for now it limits what you can connect to.

"""
from functools import partial, update_wrapper


class DBusObjectProxy(object):
    """A proxy representing an object that is owned by another connection.

    """
    def __init__(self, bus, path):
        self._dbus_bus = bus
        self._dbus_object_path = path

    @classmethod
    def create(self, bus, path, **interfaces):
        """Create a one-off object proxy instance, without defining a new class first.

        Example:

            bus = DBusObjectProxy('/org/freedesktop/DBus', bus=BusInterface)

        """
        class _DBusObjectProxyInstance(DBusObjectProxy):
            locals().update(interfaces)

        return _DBusObjectProxyInstance(path)


class DBusObjectImplementation(object):
    """Subclass this to implement your own DBus object.

    """
    def __init__(self, bus, path):
        self._dbus_bus = bus
        self._dbus_object_path = path


#XXX: How the hell do we actually make interface definitions useful to local implementations? Can we have them act like
# abstract base classes by default, and just make object proxies provide automatic implementations of them?

#TODO: Should methods and signals be implemented directly on the DBus object implementation or proxy, as properties
# indexable with the interface name if there's more than one member by the same name on a given DBus object? Difficult
# to combine multiple interfaces on an object automatically like this, and difficult to provide implementations for
# methods of local object implementations. Might be doable with decorators, but would probably require chaining like
# property.setter, or would require some sort of central registry to track what members have been implemented under
# what interfaces on a given class.

# The whole two-level thing gets really unwieldy when you have to have both definitions and implementations at both
# levels.


class _DBusDefinitionMeta(type):
    """A metaclass that defers object instantiation by one call.

    This allows classes with this metaclass to be called once to define a member:

        class ExampleInterface(DBusInterface('org.example.app'):
            foo = DBusProperty('org.example.app.foo')

    and then to actually instantiate objects later, adding the arguments from the first call:

        ExampleInterface.foo(stuff)  # This calls DBusProperty.__init__('org.example.app.foo', stuff)

    This in turn is used by _DBusInterfaceMember and _DBusInterfaceBase to bind members to their containers.

    """
    def __new__(metacls, name, bases, dict):
        cls = type.__new__(metacls, name, bases, dict)
        return lambda *args, **kwargs: partial(cls, *args, **kwargs)


class _DBusInterfaceMember(object):
    __metaclass__ = _DBusDefinitionMeta

    _dbus_interface = None

    def __get__(self, obj, objtype=None):
        return self.bind(self, obj, objtype)


class _DBusInterfaceBase(type):
    __metaclass__ = _DBusDefinitionMeta

    _dbus_object = None

    def __get__(self, obj, objtype=None):
        return self.bind(self, obj, objtype)

    def __init__(self, obj):
        self.obj = obj

    def _callMethod(self, methodName, *args, **kwargs):
        self.obj._callMethod(self.name, *args, **kwargs)


def DBusInterface(name):
    class _DBusInterfaceNamed(_DBusInterfaceBase):
        _dbus_interface_name = name

    return _DBusInterfaceNamed


#####################################
# I think it makes sense to aim for this:


class PeerInterface(DBusInterface('org.freedesktop.DBus.Peer')):
    def Ping(self):
        pass

    def GetMachineId(self):
        #FIXME: How the hell do we find/generate this? The spec doesn't seem to mention it!
        pass


# Creating and registering a local object:
class LocalPeer(DBusObjectImplementation):
    peer = PeerInterface()

localPeer = LocalPeer()
bus.registerlocalObject(localPeer)


# Creating and using a proxy for a remote object:
class RemotePeer(DBusObjectProxy):
    peer = PeerInterface()

networkManager = RemotePeer('org.freedesktop.NetworkManager')
networkManager.Ping()


#####################################


class _DBusMethod(object):
    def __init__(self, definitionFunc, name=None, ):
        self.name = name or self.definitionFunc.__name__
        self.definitionFunc = definitionFunc

    def __call__(self, interface, *args, **kwargs):
        interface._callMethod(self.name, *args, **kwargs)


class _DBusSignal(object):
    pass


class PropertiesInterface(DBusInterface('org.freedesktop.DBus.Properties')):
    @dbusSignal
    def PropertiesChanged(interfaceName, propertyName):
        "Triggered whenever a property on this object is changed."


class DBusProperty(object):
    readwrite = object()
    read = object()
    write = object()

    def __init__(self, name, access=readwrite, signalled=True):
        self.name = name

        if access is DBusProperty.read:
            del self.value_setter
        else:
            self.value = self.value.setter(self.value_setter)

        if access is DBusProperty.write:
            self.value = self.value.getter(self.value_getter_writeonly)
        else:
            del self.value_getter_writeonly

        if signalled:
            self.signal = dbusSignal()

    @property
    def value(self):
        pass

    def value_getter_writeonly(self):
        raise TypeError("Property {} is read-only!".format(self.name))

    def value_setter(self):
        pass


class Interface(object):
    def __init__(iface, interfaceName):
        iface.interfaceName = interfaceName

    def readOnlyProperty(iface, propertyName, getTransform=lambda x: x):
        @Property
        def getProperty(self):
            interface = self.getInterface('org.freedesktop.DBus.Properties')
            try:
                return getTransform(interface.Get(iface.interfaceName, propertyName))
            except dbus.DBusException:
                return None

        return getProperty

    def readOnlyPropAndSignal(iface, propertyName, getTransform=lambda x: x):
        @property
        def getSignal(self):
            return PropertySignalDispatcher.getSignal(self.targetObject, iface.interfaceName, propertyName)

        return (iface.readOnlyProperty(propertyName, getTransform), getSignal)

    def readWritePropAndSignal(iface, propertyName, getTransform=lambda x: x, setTransform=lambda x: x):
        (prop, signal) = iface.readOnlyPropAndSignal(propertyName, getTransform)

        @prop.setter
        def setProperty(self, value):
            interface = self.getInterface('org.freedesktop.DBus.Properties')
            interface.Set(iface.interfaceName, propertyName, setTransform(value))

        return (prop, signal)

    def methodAction(iface, methodName):
        def doMethod(self, *args):
            interface = self.getInterface(iface.interfaceName)
            getattr(interface, methodName)(*args)

        doMethod.__name__ = methodName

        return Action(doMethod)

    def signal(iface, signalName, description):
        @property
        def getSignal(self):
            return signal(self.targetObject, iface.interfaceName, signalName, description)

        return getSignal


## Decorators ##

class BaseDecorator(object):
    def __init__(self, wrapperClass):
        update_wrapper(self, wrapperClass)
        self.wrapperClass = wrapperClass

    def __call__(self, __wrappedOrFirstArg, *args, **kwargs):
        # We start our argument with '__' to trigger name mangling so there will be less chance of name collisions with
        # any parameters used by the wrapper class.

        if callable(__wrappedOrFirstArg):
            # First non-keyword argument is a method or class; assume we're simply being called as `@decorator`.
            wrapper = self.wrapperClass(__wrappedOrFirstArg, *args, **kwargs)
            return update_wrapper(wrapper, __wrappedOrFirstArg)

        else:
            # First non-keyword argument is not a callable; assume we're being called as `@decorator(...)`.
            return lambda *largs, **lkwargs: __wrappedOrFirstArg(*largs, **lkwargs)


dbusMethod = BaseDecorator(_DBusMethod)

dbusSignal = BaseDecorator(_DBusSignal)


"""
If a well-known bus name implies the presence of a "main" interface, that "main" interface is often given the same name as the well-known bus name, and situated at the corresponding object path. For instance, if the owner of example.com is developing a D-Bus API for a music player, they might define that any application that takes the well-known name com.example.MusicPlayer1 should have an object at the object path /com/example/MusicPlayer1 which implements the interface com.example.MusicPlayer1.
"""


"""Important header fields, and the classes they're attached to:

Object or ObjectProxy:
    - path (1: PATH)

    Method:
        - name (3: MEMBER)
        - signature (8: SIGNATURE) (can this be determined from the arguments at call time)

    Interface:
        - name (2: INTERFACE)

        Method:
            - name (3: MEMBER)
            - signature (8: SIGNATURE) (can this be determined from the arguments at call time)

        Signal:
            - name (3: MEMBER)
            - signature (8: SIGNATURE) (can this be determined from the arguments at call time)

Connection:
    - uniqueName (6: DESTINATION and 7: SENDER)
    - additionalNames[] (6: DESTINATION)

"""


class BusInterface(DBusInterface('org.freedesktop.DBus')):
    canQuit = DBusProperty('CanQuit', readonly=True)

    ## Proxies for org.freedesktop.DBus methods ##
    @dbusMethod
    def hello(self):
        '''org.freedesktop.DBus.Hello

        STRING Hello ()

        Reply arguments:

        Argument	Type	Description
        0	STRING	Unique name assigned to the connection
        Before an application is able to send messages to other applications it must send the org.freedesktop.DBus.Hello message to the message bus to obtain a unique name. If an application without a unique name tries to send a message to another application, or a message to the message bus itself that isn't the org.freedesktop.DBus.Hello message, it will be disconnected from the bus.

        There is no corresponding "disconnect" request; if a client wishes to disconnect from the bus, it simply closes the socket (or other communication channel).

        '''

    @method
    def listNames(self):
        '''org.freedesktop.DBus.ListNames

        ARRAY of STRING ListNames ()

        Reply arguments:

        Argument	Type	Description
        0	ARRAY of STRING	Array of strings where each string is a bus name
        Returns a list of all currently-owned names on the bus.

        '''

    @method
    def listActivatableNames(self):
        '''org.freedesktop.DBus.ListActivatableNames

        ARRAY of STRING ListActivatableNames ()

        Reply arguments:

        Argument	Type	Description
        0	ARRAY of STRING	Array of strings where each string is a bus name
        Returns a list of all names that can be activated on the bus.

        '''

    @method
    def nameHasOwner(self, name):
        '''org.freedesktop.DBus.NameHasOwner

        BOOLEAN NameHasOwner (in STRING name)

        Message arguments:

        Argument	Type	Description
        0	STRING	Name to check
        Reply arguments:

        Argument	Type	Description
        0	BOOLEAN	Return value, true if the name exists
        Checks if the specified name exists (currently has an owner).

        '''

    @signal
    def nameOwnerChanged(name, old_owner, new_owner):
        '''org.freedesktop.DBus.NameOwnerChanged

        NameOwnerChanged (STRING name, STRING old_owner, STRING new_owner)

        Message arguments:

        Argument	Type	Description
        0	STRING	Name with a new owner
        1	STRING	Old owner or empty string if none
        2	STRING	New owner or empty string if none
        This signal indicates that the owner of a name has changed. It's also the signal to use to detect the appearance of new names on the bus.

        '''

    @signal
    def nameLost(name):
        '''org.freedesktop.DBus.NameLost

        NameLost (STRING name)

        Message arguments:

        Argument	Type	Description
        0	STRING	Name which was lost
        This signal is sent to a specific application when it loses ownership of a name.

        '''

    @signal
    def nameAcquired(name):
        '''org.freedesktop.DBus.NameAcquired

        NameAcquired (STRING name)

        Message arguments:

        Argument	Type	Description
        0	STRING	Name which was acquired
        This signal is sent to a specific application when it gains ownership of a name.

        '''

    @method
    def startServiceByName(self, name, flags):
        '''org.freedesktop.DBus.StartServiceByName

        UINT32 StartServiceByName (in STRING name, in UINT32 flags)

        Message arguments:

        Argument	Type	Description
        0	STRING	Name of the service to start
        1	UINT32	Flags (currently not used)
        Reply arguments:

        Argument	Type	Description
        0	UINT32	Return value
        Tries to launch the executable associated with a name. For more information, see the section called "Message Bus Starting Services".

        The return value can be one of the following values:

        Identifier	Value	Description
        DBUS_START_REPLY_SUCCESS	1	The service was successfully started.
        DBUS_START_REPLY_ALREADY_RUNNING	2	A connection already owns the given name.

        '''

    @method
    def updateActivationEnvironment(self, environment):
        '''org.freedesktop.DBus.UpdateActivationEnvironment

        UpdateActivationEnvironment (in ARRAY of DICT<STRING,STRING> environment)

        Message arguments:

        Argument	Type	Description
        0	ARRAY of DICT<STRING,STRING>	Environment to add or update
        Normally, session bus activated services inherit the environment of the bus daemon. This method adds to or modifies that environment when activating services.

        Some bus instances, such as the standard system bus, may disable access to this method for some or all callers.

        Note, both the environment variable names and values must be valid UTF-8. There's no way to update the activation environment with data that is invalid UTF-8.

        '''

    @method
    def getNameOwner(self, name):
        '''org.freedesktop.DBus.GetNameOwner

        STRING GetNameOwner (in STRING name)

        Message arguments:

        Argument	Type	Description
        0	STRING	Name to get the owner of
        Reply arguments:

        Argument	Type	Description
        0	STRING	Return value, a unique connection name
        Returns the unique connection name of the primary owner of the name given. If the requested name doesn't have an owner, returns a org.freedesktop.DBus.Error.NameHasNoOwner error.

        '''

    @method
    def getConnectionUnixUser(self, bus_name):
        '''org.freedesktop.DBus.GetConnectionUnixUser

        UINT32 GetConnectionUnixUser (in STRING bus_name)

        Message arguments:

        Argument	Type	Description
        0	STRING	Unique or well-known bus name of the connection to query, such as :12.34 or com.example.tea
        Reply arguments:

        Argument	Type	Description
        0	UINT32	Unix user ID
        Returns the Unix user ID of the process connected to the server. If unable to determine it (for instance, because the process is not on the same machine as the bus daemon), an error is returned.

        '''

    @method
    def getConnectionUnixProcessID(self, bus_name):
        '''org.freedesktop.DBus.GetConnectionUnixProcessID

        UINT32 GetConnectionUnixProcessID (in STRING bus_name)

        Message arguments:

        Argument	Type	Description
        0	STRING	Unique or well-known bus name of the connection to query, such as :12.34 or com.example.tea
        Reply arguments:

        Argument	Type	Description
        0	UINT32	Unix process id
        Returns the Unix process ID of the process connected to the server. If unable to determine it (for instance, because the process is not on the same machine as the bus daemon), an error is returned.

        '''

    @method
    def addMatch(self, rule):
        '''org.freedesktop.DBus.AddMatch

        AddMatch (in STRING rule)

        Message arguments:

        Argument	Type	Description
        0	STRING	Match rule to add to the connection
        Adds a match rule to match messages going through the message bus (see the section called "Match Rules"). If the bus does not have enough resources the org.freedesktop.DBus.Error.OOM error is returned.

        '''

    @method
    def removeMatch(self, rule):
        '''org.freedesktop.DBus.RemoveMatch

        RemoveMatch (in STRING rule)

        Message arguments:

        Argument	Type	Description
        0	STRING	Match rule to remove from the connection
        Removes the first rule that matches (see the section called "Match Rules"). If the rule is not found the org.freedesktop.DBus.Error.MatchRuleNotFound error is returned.

        '''

    @method
    def getId(self, id):
        '''org.freedesktop.DBus.GetId

        GetId (out STRING id)

        Reply arguments:
        0	STRING	Unique ID identifying the bus daemon

        '''


#XXX: The spec doesn't actually say what path the org.freedesktop.DBus messages should be sent to! I had to guess.
class Bus(DBusObjectProxy('/org/freedesktop/DBus')):
    dbus = BusInterface()


#### Old EFL-based implementation ####

from abc import ABCMeta, abstractproperty
import logging

import dbus

import e_dbus

from .controllers import BaseController, Action, Property
from .signals import Signal


logger = logging.getLogger('epsb.dbus_util')

dbus_ml = e_dbus.DBusEcoreMainLoop()
bus = dbus.SessionBus(mainloop=dbus_ml)


class DBusController(BaseController):
    __metaclass__ = ABCMeta

    __interfaceCache = {}

    def __init__(self):
        super(DBusController, self).__init__()

    @abstractproperty
    def targetObject(self):
        pass

    def getInterface(self, interfaceName):
        key = (self.targetObject, interfaceName)
        try:
            return self.__interfaceCache[key]
        except KeyError:
            interface = dbus.Interface(self.targetObject, dbus_interface=interfaceName)
            self.__interfaceCache[key] = interface
            return interface


def signal(targetObject, interfaceName, signalName, description):
    sig = Signal(description)
    targetObject.connect_to_signal(signalName, sig, dbus_interface=interfaceName)
    return sig


class PropertySignalDispatcher(object):
    _dispatchersByObject = {}

    def __init__(self, targetObject):
        self.targetObject = targetObject

        self.propChangedSignal = signal(
                targetObject,
                'org.freedesktop.DBus.Properties',
                'PropertiesChanged',
                "Triggered whenever a property on this object is changed."
                )
        self.propChangedSignal.connect(self._onPropertiesChanged)

        self.propertySignals = {}

    def getSignalForProperty(self, interfaceName, propertyName):
        key = (interfaceName, propertyName)
        try:
            return self.propertySignals[key]
        except KeyError:
            sig = Signal("Triggered when {} is changed.".format(propertyName))
            self.propertySignals[key] = sig
            return sig

    def _onPropertiesChanged(self, interfaceName, changedProperties, invalidatedProperties):
        for prop, newValue in changedProperties.items():
            try:
                self.propertySignals[(interfaceName, prop)](newValue)
            except KeyError:
                pass

        for prop in invalidatedProperties:
            try:
                self.propertySignals[(interfaceName, prop)]()
            except KeyError:
                pass

    @classmethod
    def getSignal(cls, targetObject, interfaceName, propertyName):
        try:
            dispatcher = cls._dispatchersByObject[targetObject]
        except KeyError:
            dispatcher = cls(targetObject)
            cls._dispatchersByObject[targetObject] = dispatcher

        return dispatcher.getSignalForProperty(interfaceName, propertyName)


class Interface(object):
    def __init__(iface, interfaceName):
        iface.interfaceName = interfaceName

    def readOnlyProperty(iface, propertyName, getTransform=lambda x: x):
        @Property
        def getProperty(self):
            interface = self.getInterface('org.freedesktop.DBus.Properties')
            try:
                return getTransform(interface.Get(iface.interfaceName, propertyName))
            except dbus.DBusException:
                return None

        return getProperty

    def readOnlyPropAndSignal(iface, propertyName, getTransform=lambda x: x):
        @property
        def getSignal(self):
            return PropertySignalDispatcher.getSignal(self.targetObject, iface.interfaceName, propertyName)

        return (iface.readOnlyProperty(propertyName, getTransform), getSignal)

    def readWritePropAndSignal(iface, propertyName, getTransform=lambda x: x, setTransform=lambda x: x):
        (prop, signal) = iface.readOnlyPropAndSignal(propertyName, getTransform)

        @prop.setter
        def setProperty(self, value):
            interface = self.getInterface('org.freedesktop.DBus.Properties')
            interface.Set(iface.interfaceName, propertyName, setTransform(value))

        return (prop, signal)

    def methodAction(iface, methodName):
        def doMethod(self, *args):
            interface = self.getInterface(iface.interfaceName)
            getattr(interface, methodName)(*args)

        doMethod.__name__ = methodName

        return Action(doMethod)

    def signal(iface, signalName, description):
        @property
        def getSignal(self):
            return signal(self.targetObject, iface.interfaceName, signalName, description)

        return getSignal
