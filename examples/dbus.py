# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: Simple D-Bus example

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import logging

from fttpwm import logconfig


logconfig.configure()

logger = logging.getLogger("examples.dbus")


import fttpwm.dbus
import fttpwm.dbus.bus
import fttpwm.dbus.local
import fttpwm.dbus.remote
import fttpwm.dbus.proto.types

try:
    from fttpwm.eventloop.zmq_loop import ZMQEventLoop

    eventloop = ZMQEventLoop()
    logger.info("Using the ZeroMQ event loop.")

except ImportError:
    logger.warn("Couldn't import ZeroMQ event loop! Falling back to polling event loop.", exc_info=True)

    from fttpwm.eventloop.poll_loop import PollEventLoop

    eventloop = PollEventLoop()


bus = fttpwm.dbus.bus.SessionBus()


##### Example exported local object from dbus-python's dbus.service.Object's docstring (corrected) #####

#class Example(dbus.service.Object):
#    def __init__(self, object_path):
#        dbus.service.Object.__init__(self, dbus.SessionBus(), object_path)
#        self._last_input = None
#
#    @dbus.service.method(interface='com.example.Sample', in_signature='v', out_signature='s')
#    def StringifyVariant(self, var):
#        self.LastInputChanged(var)      # emits the signal
#        return str(var)
#
#    @dbus.service.signal(interface='com.example.Sample', signature='v')
#    def LastInputChanged(self, var):
#        # run just before the signal is actually emitted
#        # just put "pass" if nothing should happen
#        self._last_input = var
#
#    @dbus.service.method(interface='com.example.Sample', in_signature='', out_signature='v')
#    def GetLastInput(self):
#        return self._last_input


##### Our version of the above example #####

### The interface ###
class SampleInterface(fttpwm.dbus.interface.DBusInterface('com.example.Sample')):
    @fttpwm.dbus.interface.Method(inSig='v', outSig='s')
    def StringifyVariant(self, var):
        """Turn the given Variant into a String.

        """

    @fttpwm.dbus.interface.Signal(sig='v')
    def LastInputChanged(self, var):
        """Emitted whenever StringifyVariant gets called with a different input.

        """

    @fttpwm.dbus.interface.Method(inSig='', outSig='v')
    def GetLastInput(self):
        """Get the last value passed to StringifyVariant.

        """


# Or, alternate way of defining the interface: (not sure which I like better, or whether we can support both of these)
class SampleInterface(fttpwm.dbus.interface.DBusInterface('com.example.Sample')):
    StringifyVariant = fttpwm.dbus.interface.Method(inSig='v', outSig='s',
            doc="Turn the given Variant into a String.")
    LastInputChanged = fttpwm.dbus.interface.Signal(sig='v',
            doc="Emitted whenever StringifyVariant gets called with a different input.")
    GetLastInput = fttpwm.dbus.interface.Method(inSig='', outSig='v',
            doc="Get the last value passed to StringifyVariant.")


### The exported object ###
class Example(fttpwm.dbus.local.Object):
    def __init__(self, object_path, bus=None):
        if bus is None:
            bus = fttpwm.singletons.dbusSessionBus
        super(Example, self).__init__(object_path, bus)
        self._last_input = None

    @SampleInterface.StringifyVariant
    def StringifyVariant(self, var):
        self.LastInputChanged(var)  # emits the signal
        return str(var)

    @SampleInterface.LastInputChanged
    def LastInputChanged(self, var):
        # run just before the signal is actually emitted
        # just put "pass" if nothing should happen
        self._last_input = var

    @SampleInterface.GetLastInput
    def GetLastInput(self):
        return self._last_input


# Alternate way of defining the object: (pretty sure I like this better than the above, but both can be supported)
class Example(fttpwm.dbus.SessionBus().localObject):
    def __init__(self, object_path):
        super(Example, self).__init__(object_path)
        self._last_input = None

    @SampleInterface.StringifyVariant
    def StringifyVariant(self, var):
        self.LastInputChanged(var)  # emits the signal
        return str(var)

    @SampleInterface.LastInputChanged
    def LastInputChanged(self, var):
        # run just before the signal is actually emitted
        # just put "pass" if nothing should happen
        self._last_input = var

    @SampleInterface.GetLastInput
    def GetLastInput(self):
        return self._last_input


### Creating a remote proxy object ###
class RemoteExample(fttpwm.dbus.remote.Object):
    sample = SampleInterface()

example = RemoteExample(
        bus,  # Our connection to the bus
        '/com/example/Sample',  # The remote object's path
        'com.example.Sample'  # The bus name of the connection this remote object lives on
        )


# Alternate way of creating remote object proxies: (both can be supported)
example = bus.remoteObject(
        '/com/example/Sample',
        SampleInterface,  # More than one interface can be defined, so bus_name must be a kwarg
        bus_name='com.example.Sample'
        )


### Calling a method on a remote proxy object ###
example.StringifyVariant("Some value!")

# Or, specifying a full type:
example.StringifyVariant(fttpwm.dbus.proto.types.Variant(fttpwm.dbus.proto.types.String, "Some value!"))


# If more than one interface on the remote object defines the same method, we need to specify which interface to use:
example.sample.StringifyVariant("Some value!")

# Alternates: (not sure which of these I prefer)
example.StringifyVariant[SampleInterface]("Some value!")

example[SampleInterface].StringifyVariant("Some value!")

# Another alternate; naming all methods as 'InterfaceName_MethodName':
example.SampleInterface_StringifyVariant("Some value!")


##########################################


#XXX: How the hell do we actually make interface definitions useful to local implementations? Can we have them act like
# abstract base classes by default, and just make remote object proxies provide automatic implementations of them?

#TODO: Should methods and signals be implemented directly on the DBus object implementation or proxy, as properties
# indexable with the interface name if there's more than one member by the same name on a given DBus object? Difficult
# to combine multiple interfaces on an object automatically like this, and difficult to provide implementations for
# methods of local object implementations. Might be doable with decorators, but would probably require chaining like
# property.setter, or would require some sort of central registry to track what members have been implemented under
# what interfaces on a given class.

# The whole two-level thing gets really unwieldy when you have to have both definitions and implementations at both
# levels.


class PeerInterface(fttpwm.dbus.interface.Interface('org.freedesktop.DBus.Peer')):
    def Ping(self):
        pass

    def GetMachineId(self):
        pass


# Creating and exporting a local object:
class LocalPeer(fttpwm.dbus.local.Object):
    @PeerInterface.Ping
    def peer_Ping(self):
        # This should generate an empty METHOD_RETURN message.
        pass

    @PeerInterface.GetMachineId
    def peer_GetMachineId(self):
        #FIXME: How the hell do we find/generate this? The spec doesn't seem to mention it!
        return '07b6ac7a4c79d9b9628392f30000bea1'

localPeer = LocalPeer(bus, '/org/freedesktop/DBus/Peer')


# Creating and using a proxy for a remote object:
class RemotePeer(fttpwm.dbus.remote.Object):
    peer = PeerInterface()

networkManager = RemotePeer(bus, '/org/freedesktop/NetworkManager', 'org.freedesktop.NetworkManager')
networkManager.Ping()


# Or, an alternate for remote object proxies:

networkManager = bus.remoteObject('/org/freedesktop/NetworkManager',
        PeerInterface,
        bus_name='org.freedesktop.NetworkManager'
        )
networkManager.Ping()
