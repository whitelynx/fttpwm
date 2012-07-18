# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: D-Bus local object implementation base class

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""


class LocalObjectMeta(type):
    def __new__(mcs, name, bases, dict):
        for member in dict.keys:
            dict[member] = dict[member]

        return type.__new__(mcs, name, bases, dict)


class LocalObject(object):
    """

    Example:

        class Example(LocalObject):
            def __init__(self, object_path, bus=None):
                if bus is None:
                    bus = fttpwm.singletons.dbusSessionBus
                super(Example, self).__init__(object_path, bus)
                self._last_input = None

            @SampleInterface.StringifyVariant
            def StringifyVariant(self, var):
                '''Turn the given Variant into a String.

                '''
                self.LastInputChanged(var)  # emits the signal
                return str(var)

            @SampleInterface.LastInputChanged
            def LastInputChanged(self, var):
                '''Emitted whenever StringifyVariant gets called with a different input.

                '''
                # This is run just before the signal is actually emitted; just use 'pass' if nothing should happen.
                self._last_input = var

            @SampleInterface.GetLastInput
            def GetLastInput(self):
                '''Get the last value passed to StringifyVariant.

                '''
                return self._last_input

    """
    __metaclass__ = LocalObjectMeta
