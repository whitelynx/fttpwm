# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
"""FTTPWM: D-Bus local object implementation base class

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from collections import defaultdict
import logging
import warnings
from weakref import WeakSet

from .. import singletons
from ..utils import listpl, naturalJoin

from .interface import _BaseInterfaceMemberInfo
from .utils import MethodWrapper


logger = logging.getLogger('fttpwm.dbus.local')


class UnimplementedMemberWarning(UserWarning):
    pass


class _LocalObjectMeta(type):
    """Metaclass for locally-implemented DBus objects.

    Tracks all implemented interface members, warns about unimplemented interface methods, adds signals from
    implemented interfaces, and checks for duplicate member names from different interfaces, replacing each such member
    with a mapping of interface names to members.

    """
    def __new__(mcs, name, bases, dict_):
        # Track all implemented interface members.
        membersByInterface = defaultdict(set)
        membersByDBusName = defaultdict(set)
        for member in dict_.values():
            if isinstance(member, _BaseInterfaceMemberInfo):
                membersByInterface[member.dbus_interface].add(member)
                membersByDBusName[member.dbus_name].add(member)

        for interface, members in membersByInterface.items():
            # Check for unimplemented interface members.
            unimplemented = []
            for method in interface._DBusInterface_getMethods():
                if method not in members:
                    unimplemented.append(method.dbus_name)

            if len(unimplemented) > 0:
                warnings.warn(
                        "Class {!r} implements the {} from interface {!r}, but is missing {}!".format(
                            name,
                            listpl((m.dbus_name for m in members), 'method'),
                            interface.dbus_name,
                            naturalJoin(unimplemented)
                            ),
                        UnimplementedMemberWarning,
                        stacklevel=2
                        )

            # Add signal wrappers for all signals of this interface.
            for signal in interface._DBusInterface_getSignals():
                membersByDBusName[signal.dbus_name].add(signal())

            #TODO: Properties!

        dict_['_dbus_interfaces'] = WeakSet(membersByInterface.keys())

        for memberName, members in membersByDBusName.items():
            dict_[memberName] = MethodWrapper(memberName, members)

        return type.__new__(mcs, name, bases, dict_)


class LocalObject(object):
    """

    Example:

        class Example(LocalObject):
            def __init__(self, object_path, bus=None):
                super(Example, self).__init__(object_path, bus)
                self._last_input = None

            @SampleInterface.StringifyVariant
            def SampleInterface_StringifyVariant(self, var):
                '''Turn the given Variant into a String.

                '''
                self.LastInputChanged(var)  # emits the signal
                return str(var)

            @SampleInterface.LastInputChanged
            def SampleInterface_LastInputChanged(self, var):
                '''Emitted whenever StringifyVariant gets called with a different input.

                '''
                # This is run just before the signal is actually emitted; just use 'pass' if nothing should happen.
                self._last_input = var

            @SampleInterface.GetLastInput
            def SampleInterface_GetLastInput(self):
                '''Get the last value passed to StringifyVariant.

                '''
                return self._last_input

    """
    __metaclass__ = _LocalObjectMeta

    def __init__(self, object_path, bus=None):
        self.dbus_path = object_path

        if bus is None:
            bus = singletons.dbusSessionBus
        self.dbus_bus = bus


def test():
    from .interface import _createSampleInterface

    SampleInterface = _createSampleInterface()

    class Example(LocalObject):
        def __init__(self, object_path, bus=None):
            super(Example, self).__init__(object_path, bus)
            self._last_input = None

        @SampleInterface.StringifyVariant
        def SampleInterface_StringifyVariant(self, var):
            '''Turn the given Variant into a String.

            '''
            self.LastInputChanged(var)  # emits the signal
            return str(var)

        @SampleInterface.LastInputChanged
        def SampleInterface_LastInputChanged(self, var):
            '''Emitted whenever StringifyVariant gets called with a different input.

            '''
            # This is run just before the signal is actually emitted; just use 'pass' if nothing should happen.
            self._last_input = var

        @SampleInterface.GetLastInput
        def SampleInterface_GetLastInput(self):
            '''Get the last value passed to StringifyVariant.

            '''
            return self._last_input

    print(unicode(Example), repr(Example), dir(Example))
    print(Example.__doc__)
    print(Example._dbus_interfaces)

    example = Example('/com/foo/bar')
    print(unicode(example), repr(example), dir(example))
    print(example.__doc__)
    print(unicode(example.LastInputChanged), repr(example.LastInputChanged), dir(example.LastInputChanged))
    print(example.LastInputChanged.__doc__)
    print(unicode(example.GetLastInput), repr(example.GetLastInput), dir(example.GetLastInput))
    print(example.GetLastInput.__doc__)


if __name__ == '__main__':
    test()
