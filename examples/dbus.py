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
from fttpwm.dbus.interface import DBusInterface, Method, Signal

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
class Sample(DBusInterface('com.example.Sample')):
    @Method(inSig='v', outSig='s')
    def StringifyVariant(self, var):
        """Turn the given Variant into a String.

        """

    @Signal(sig='v')
    def LastInputChanged(self, var):
        """Emitted whenever StringifyVariant gets called with a different input.

        """

    @Method(inSig='', outSig='v')
    def GetLastInput(self):
        """Get the last value passed to StringifyVariant.

        """


### The exported object ###
class Example(fttpwm.dbus.local.LocalObject):
    def __init__(self, object_path, bus=None):
        if bus is None:
            bus = fttpwm.singletons.dbusSessionBus
        super(Example, self).__init__(object_path, bus)
        self._last_input = None

    @Sample.StringifyVariant
    def StringifyVariant(self, var):
        self.LastInputChanged(var)  # emits the signal
        return str(var)

    @Sample.LastInputChanged
    def LastInputChanged(self, var):
        # run just before the signal is actually emitted
        # just put "pass" if nothing should happen
        self._last_input = var

    @Sample.GetLastInput
    def GetLastInput(self):
        return self._last_input


### Creating a remote proxy object ###
class RemoteExample(fttpwm.dbus.remote.RemoteObject):
    sample = Sample()

example = RemoteExample(
        bus,  # Our connection to the bus
        '/com/example/Sample',  # The remote object's path
        'com.example.Sample'  # The bus name of the connection this remote object lives on
        )


# Alternate way of creating remote object proxies: (both can be supported; not sure if we want to support this way)
example = bus.remoteObject(
        '/com/example/Sample',
        Sample,  # More than one interface can be defined, so bus_name must be a kwarg
        bus_name='com.example.Sample'
        )


### Calling a method on a remote proxy object ###
example.StringifyVariant("Some value!")

# Or, specifying a full type:
example.StringifyVariant(fttpwm.dbus.proto.types.Variant(fttpwm.dbus.proto.types.String, "Some value!"))


# If more than one interface on the remote object defines the same method, we need to specify which interface to use:
example.sample.StringifyVariant("Some value!")

# Alternates: (not sure which of these I prefer)
example.StringifyVariant[Sample]("Some value!")


##########################################


# Creating and exporting a local object:
class LocalPeer(fttpwm.dbus.local.Object):
    @Peer.Ping
    def peer_Ping(self):
        # This should generate an empty METHOD_RETURN message.
        pass

    @Peer.GetMachineId
    def peer_GetMachineId(self):
        #FIXME: How the hell do we find/generate this? The spec doesn't seem to mention it!
        return '07b6ac7a4c79d9b9628392f30000bea1'

localPeer = LocalPeer(bus, '/org/freedesktop/DBus/Peer')


# Creating and using a proxy for a remote object:
class RemotePeer(fttpwm.dbus.remote.Object):
    peer = Peer()

networkManager = RemotePeer(bus, '/org/freedesktop/NetworkManager', 'org.freedesktop.NetworkManager')
networkManager.Ping()


# Or, an alternate for remote object proxies:

networkManager = bus.remoteObject('/org/freedesktop/NetworkManager',
        Peer,
        bus_name='org.freedesktop.NetworkManager'
        )
networkManager.Ping()
