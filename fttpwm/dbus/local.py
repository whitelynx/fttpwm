# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
"""FTTPWM: D-Bus local object implementation base class

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from collections import defaultdict
import logging
from weakref import WeakSet, WeakKeyDictionary, WeakValueDictionary

from .interface import _InterfaceMethodInfo
from ..utils import naturalJoin


logger = logging.getLogger('fttpwm.dbus.local')


class _MemberWrapper(WeakKeyDictionary):
    def __init__(self, memberName, members, **overrides):
        super(_MemberWrapper, self).__init__(
                (m.interface(), m) for m in members
                )
        self.update(overrides)

        self.__name__ = memberName

    def __call__(self, *args, **kwargs):
        if len(self) == 1:
            self.values()[0](*args, **kwargs)
        else:
            raise TypeError(
                    '{} has {} overloads in different interfaces! You must call {}[SomeInterface](...) instead.'
                        .format(self.__name, len(self), self.__name__)
                    )


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
            if isinstance(member, _InterfaceMethodInfo):
                ifaceMethod = member.interfaceMethod

                membersByInterface[ifaceMethod.interface()].add(ifaceMethod)
                membersByDBusName[ifaceMethod.methodName].add(ifaceMethod)

        for interface, members in membersByInterface.items():
            # Check for unimplemented interface members.
            unimplemented = []
            for method in interface._DBusInterface_getMethods():
                if method not in members:
                    unimplemented.append(method.methodName)

            if len(unimplemented) > 0:
                logger.warn("Class %r implements the methods %s from interface %r, but is missing %s!",
                        name,
                        naturalJoin(m.methodName for m in members),
                        interface._dbus_interfaceName,
                        naturalJoin(unimplemented)
                        )

            # Add signal wrappers for all signals of this interface.
            for signal in interface._DBusInterface_getSignals():
                if signal.signalName not in membersByDBusName:
                    membersByDBusName[signal.signalName].add(signal())

        dict_['_dbus_interfaces'] = WeakSet(membersByInterface.keys())

        interfaceMembersByName = WeakValueDictionary()
        for memberName, members in membersByDBusName.items():
            print('members with name {!r} present in interfaces: {}'.format(
                    memberName, ', '.join(member.interfaceName for member in members)))
            dict_[memberName] = _MemberWrapper(memberName, members)

            interfaceMembersByName[memberName] = members

        dict_['_dbus_interfaceMembersByName'] = interfaceMembersByName

        return type.__new__(mcs, name, bases, dict_)


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

    def __init__(self, object_path, bus):
        self._dbus_path = object_path
        self._dbus_bus = bus


def test():
    from .interface import _createSampleInterface
    from .. import singletons

    SampleInterface = _createSampleInterface()

    class Example(LocalObject):
        def __init__(self, object_path, bus=None):
            if bus is None:
                bus = singletons.dbusSessionBus
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

    example = Example('/com/foo/bar')
    print(unicode(example), repr(example), dir(example))
    print(example.__doc__)
    print(unicode(example.LastInputChanged), repr(example.LastInputChanged), dir(example.LastInputChanged))
    print(example.LastInputChanged.__doc__)
    print(unicode(example.GetLastInput), repr(example.GetLastInput), dir(example.GetLastInput))
    print(example.GetLastInput.__doc__)
