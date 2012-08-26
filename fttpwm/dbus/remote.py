# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: D-Bus remote object proxy class

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""


class RemoteObject(object):
    """The base class for proxy objects which allow interacting with remote DBus objects.

    In order to make a new proxy object, you must first define a subclass which contains the needed interfaces as
    member variables. Instances of that subclass will have members corresponding to all members of the interfaces
    contained in the class.

    `RemoteObject` subclass instances represent members of the remote object with instances of a custom class that
    allows disambiguation between members of different interfaces which share the same name. If two or more interfaces
    on a `RemoteObject` subclass contain members with the same name, those members must be indexed by the interface you
    wish to work with when you use them:

        cb = remoteObj.Get[PropertiesInterface]("propName")

    Calling a method on a remote object is almost identical to normal Python, with the exception of keyword arguments.
    Passing method arguments as keyword arguments is not yet supported (FIXME!), and there is a special keyword
    argument: `dbus_destination`. This specifies which connection to send the method call to. If you are using a
    `RemoteObject` subclass instance with a message bus (as opposed to a direct connection), you MUST either specify
    the destination connection name when instantiating the object, or specify it as the `dbus_destination` keyword
    argument when calling any method on the remote object.

    Method calls return a new `fttpwm.dbus.connection.Callbacks` object bound to the method call request; you can
    assign your own functions to its `onReturn` and `onError` properties in order to handle return values and errors.
    They are not `fttpwm.signals.Signal` instances yet, because of the desire to avoid race conditions by allowing
    callbacks to be called immediately if they are assigned after the return or error event has already occurred.

    Signals on remote objects are represented by `fttpwm.signals.Signal` instances.

    #TODO: Describe properties on remote objects!

    Example:

        class RemoteExample(RemoteObject):
            sample = SampleInterface()

        example = RemoteExample(
                bus,                    # Our connection to the bus
                '/com/example/Sample',  # The remote object's path
                'com.example.Sample'    # The bus name of the connection this remote object lives on (optional)
                )

        # Calling a method on a remote proxy object:
        example.StringifyVariant("Some value!")

        # Or, specifying full types:
        example.StringifyVariant(fttpwm.dbus.proto.types.Variant(fttpwm.dbus.proto.types.String, "Some value!"))

        # If more than one interface on the remote object defines the same method, specify which interface to use:
        example.sample.StringifyVariant("Some value!")

        # Another way to specify the interface:
        example.StringifyVariant[SampleInterface]("Some value!")

    """
    #FIXME: Implement!
