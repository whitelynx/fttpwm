# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: D-Bus remote object proxy class

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""


class RemoteObject(object):
    """

    Example:

        class RemoteExample(RemoteObject):
            sample = SampleInterface()

        example = RemoteExample(
                bus,                    # Our connection to the bus
                '/com/example/Sample',  # The remote object's path
                'com.example.Sample'    # The bus name of the connection this remote object lives on
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
