# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
"""FTTPWM: D-Bus interface definition classes

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from abc import ABCMeta, abstractmethod
from weakref import ref

from .. import signals


#### Decorators ####

def Method(inSig='', outSig='', resultFields=None):
    """D-Bus interface method decorator

    Example:

        class SampleInterface(DBusInterface('com.example.Sample')):
            @Method(inSig='v', outSig='s')
            def StringifyVariant(self, var):
                '''Turn the given Variant into a String.

                '''
            # ... other members ...

    """
    return lambda func: _InterfaceMethod(func, inSig, outSig, resultFields)


def Signal(sig=''):
    """D-Bus interface signal decorator

    Example:

        class SampleInterface(DBusInterface('com.example.Sample')):
            @Signal(sig='v')
            def LastInputChanged(self, var):
                '''Emitted whenever StringifyVariant gets called with a different input.

                '''
            # ... other members ...

    """
    return lambda func: _InterfaceSignal(func, sig)


#### Interfaces ####

class _BaseDBusInterface(object):
    pass


def DBusInterface(interfaceName):
    """D-Bus interface base class factory

    Example:

        class SampleInterface(DBusInterface('com.example.Sample')):
            '''A sample D-Bus interface

            '''
            @Method(inSig='v', outSig='s')
            def StringifyVariant(self, var):
                '''Turn the given Variant into a String.

                '''

            @Signal(sig='v')
            def LastInputChanged(self, var):
                '''Emitted whenever StringifyVariant gets called with a different input.

                '''

            @Method(inSig='', outSig='v')
            def GetLastInput(self):
                '''Get the last value passed to StringifyVariant.

                '''

    """
    class _DBusInterface(_BaseDBusInterface):
        __doc__ = """D-Bus interface base class for the {} interface

        """.format(interfaceName)
        dbus_name = interfaceName

        def __init__(self, *args, **kwargs):
            raise TypeError("You cannot instantiate interfaces!")

        @classmethod
        def _DBusInterface_getMembers(cls):
            for memberName in dir(cls):
                yield (memberName, getattr(cls, memberName))

        @classmethod
        def _DBusInterface_getSignals(cls):
            for memberName, member in cls._DBusInterface_getMembers():
                if isinstance(member, _InterfaceSignal):
                    yield member

        @classmethod
        def _DBusInterface_getMethods(cls):
            for memberName, member in cls._DBusInterface_getMembers():
                if isinstance(member, _InterfaceMethod):
                    yield member

        #TODO: Properties!

    return _DBusInterface


#### Interface Members ####

class _BaseInterfaceMember(object):
    """Base D-Bus interface member class

    """
    _dbus_wrapper_class = None

    def __init__(self, func):
        self.dbus_name = func.__name__
        self.__doc__ = func.__doc__
        self._dbus_interface = None

    def __get__(self, instance, owner):
        self._dbus_interface = ref(owner)
        return self

    def __unicode__(self):
        return u'{}.{}'.format(self.dbus_interface_name, self.dbus_name)

    def __call__(self, wrappedFunc=None):
        wrapper = self._dbus_wrapper_class(self, wrappedFunc)
        wrapper.__name__ = '{}'.format(self.dbus_name)
        wrapper.__doc__ = self.__doc__
        return wrapper

    @property
    def dbus_interface(self):
        return self._dbus_interface()

    @property
    def dbus_interface_name(self):
        return self.dbus_interface.dbus_name


class _InterfaceMethod(_BaseInterfaceMember):
    """D-Bus interface method class

    """
    def __init__(self, func, inSig='', outSig='', resultFields=None):
        self._dbus_wrapper_class = _InterfaceMethodInfo

        super(_InterfaceMethod, self).__init__(func)

        self.dbus_in_signature = inSig
        self.dbus_out_signature = outSig

        self.resultFields = resultFields
        if isinstance(resultFields, basestring):
            self.resultFields = resultFields.split()

    def __repr__(self):
        return u'<DBus interface method {}.{}>'.format(self.dbus_interface_name, self.dbus_name)


class _InterfaceSignal(_BaseInterfaceMember):
    """D-Bus interface signal class

    """
    def __init__(self, func, sig=''):
        self._dbus_wrapper_class = _InterfaceSignalInfo

        super(_InterfaceSignal, self).__init__(func)

        self.signature = sig

    def __repr__(self):
        return u'<DBus interface signal {}.{}>'.format(self.dbus_interface_name, self.dbus_name)


#### DBus Object Members ####

class _BaseInterfaceMemberInfo(object):
    """D-Bus interface member information, for wrapping interface members in DBus objects.

    """
    __metaclass__ = ABCMeta

    def __init__(self, interfaceMember, wrappedFunction):
        super(_BaseInterfaceMemberInfo, self).__init__()

        self.dbus_member = interfaceMember
        self._dbus_object = None
        self._dbus_wrapped_func = wrappedFunction

    def __get__(self, instance, owner):
        self.dbus_object = instance
        return self

    @property
    def dbus_name(self):
        return self.dbus_member.dbus_name

    @property
    def dbus_object(self):
        return self._dbus_object()

    @dbus_object.setter
    def dbus_object(self, instance):
        self._dbus_object = ref(instance)

    @property
    def dbus_interface(self):
        return self.dbus_member.dbus_interface

    @property
    def dbus_interface_name(self):
        return self.dbus_member.dbus_interface_name

    @property
    def dbus_bus(self):
        return self.dbus_object.dbus_bus

    @property
    def dbus_path(self):
        return self.dbus_object.dbus_path


class _CallableInterfaceMemberInfo(_BaseInterfaceMemberInfo):
    """D-Bus interface member information, for wrapping interface members in DBus objects.

    """
    def __init__(self, interfaceMember, wrappedMethod):
        super(_CallableInterfaceMemberInfo, self).__init__(interfaceMember, wrappedMethod)
        self._dbus_do_call = None

    @_BaseInterfaceMemberInfo.dbus_object.setter
    def dbus_object(self, instance):
        self._dbus_object = ref(instance)

        try:
            remote = globals()['remote']
        except:
            from . import remote
            globals()['remote'] = remote

        if isinstance(instance, remote.RemoteObject):
            self._dbus_do_call = self.dbus_remote_call
        else:
            self._dbus_do_call = self.dbus_local_call

        return self

    def __call__(self, *args, **kwargs):
        return self._dbus_do_call(*args, **kwargs)

    @abstractmethod
    def dbus_local_call(self, *args, **kwargs):
        """Handle an incoming call to this member.

        """

    @abstractmethod
    def dbus_remote_call(self, *args, **kwargs):
        """Handle an outgoing call to this member.

        """


## Methods ##

class _InterfaceMethodInfo(_CallableInterfaceMemberInfo):
    """D-Bus interface method information, for wrapping local implementation methods and methods on remote objects.

    """
    def __init__(self, interfaceMethod, wrappedMethod):
        super(_InterfaceMethodInfo, self).__init__(interfaceMethod, wrappedMethod)

    def dbus_local_call(self, *args, **kwargs):
        """Handle an incoming call to this member.

        Call the wrapped method on the local implementation object.

        """
        return self._dbus_wrapped_func(self.dbus_object, *args, **kwargs)

    def dbus_remote_call(self, *args, **kwargs):
        """Handle an outgoing call to this member.

        Send a `METHOD_CALL` message for this member to the remote object.

        In addition to the arguments accepted by the wrapped method, an additional keyword-only argument is accepted:
        - `dbus_destination`: Tells the bus to only send the method call to the given connection

        This method will do two things:
        - If this wrapper was instantiated using a decorator, the decorated method will be called.
        - A `METHOD_CALL` message will be sent to the connected peer.  This message will have `PATH` set to the path of
            the DBus object this wrapper is bound to, `INTERFACE` set to the name of the interface in which this method
            was defined, and `MEMBER` set to the method's name. The message will also have `DESTINATION` set to the
            value of the `dbus_destination` keyword argument, if given.

        @returns a new `fttpwm.dbus.connection.Callbacks` object for this method call

        """
        if self._dbus_wrapped_func is not None:
            self._dbus_wrapped_func(self.dbus_object, *args, **kwargs)

        destination = kwargs.pop('dbus_destination', self.dbus_object.dbus_destination)

        if len(kwargs) > 0:
            raise NotImplementedError("Calling methods with explicit keyword arguments is not yet supported!")

        return self.dbus_bus.callMethod(
                self.dbus_path,
                self.dbus_name,
                inSignature=self.dbus_member.dbus_in_signature,
                args=args,
                interface=self.dbus_interface_name,
                destination=destination
                )


## Signals ##

class _InterfaceSignalInfo(_CallableInterfaceMemberInfo):
    def __init__(self, interfaceSignal, wrappedMethod):
        super(_InterfaceSignalInfo, self).__init__(interfaceSignal, wrappedMethod)
        self.__signal = signals.Signal()

    def __getattr__(self, name):
        return getattr(self.__signal, name)

    def dbus_local_call(self, *args, **kwargs):
        """Handle an incoming call to this member.

        Call the local implementation object's handler for this signal.

        Handle this signal. Call the wrapped method on the local implementation object.

        """
        if self._dbus_wrapped_func is not None:
            self._dbus_wrapped_func(self.dbus_object, *args, **kwargs)

    def dbus_remote_call(self, *args, **kwargs):
        """Handle an outgoing call to this member.

        Emit this signal.

        In addition to the arguments accepted by the wrapped signal, an additional keyword-only argument is accepted:
        - `dbus_destination`: Tells the bus to only send the signal to the given connection

        This method will do three things:
        - If this wrapper was instantiated using a decorator, the decorated method will be called.
        - All local signal handlers for this signal will be called, just like with `fttpwm.signals.Signal`.
        - A `SIGNAL` message will be sent to the bus, notifying other clients that the signal has been emitted. This
            message will have `PATH` set to the path of the DBus object this wrapper is bound to, `INTERFACE` set to
            the name of the interface in which this signal was defined, and `MEMBER` set to the signal's name. The
            message will also have `DESTINATION` set to the value of the `dbus_destination` keyword argument, if given.

        """
        if self._dbus_wrapped_func is not None:
            self._dbus_wrapped_func(self.dbus_object, *args, **kwargs)

        self.__signal(*args, **kwargs)

        destination = kwargs.pop('dbus_destination', None)

        if len(kwargs) > 0:
            raise NotImplementedError("Emitting signals with explicit keyword arguments is not yet supported!")

        #def emitSignal(self, objectPath, member, signature='', args=[], interface=None, destination=None):
        self.dbus_bus.emitSignal(
                self.dbus_path,
                self.dbus_name,
                signature=self.dbus_member.dbus_signature,
                args=args,
                interface=self.dbus_interface_name,
                destination=destination
                )


#### Testing ####

def _createSampleInterface():
    class SampleInterface(DBusInterface('com.example.Sample')):
        '''A sample D-Bus interface

        '''
        @Method(inSig='v', outSig='s')
        def StringifyVariant(self, var):
            '''Turn the given Variant into a String.

            '''

        @Signal(sig='v')
        def LastInputChanged(self, var):
            '''Emitted whenever StringifyVariant gets called with a different input.

            '''

        @Method(inSig='', outSig='v')
        def GetLastInput(self):
            '''Get the last value passed to StringifyVariant.

            '''

    return SampleInterface


def test():
    SampleInterface = _createSampleInterface()

    print(unicode(SampleInterface), repr(SampleInterface), dir(SampleInterface))
    print(SampleInterface.__doc__)
    print(unicode(SampleInterface.LastInputChanged), repr(SampleInterface.LastInputChanged),
            dir(SampleInterface.LastInputChanged))
    print(SampleInterface.LastInputChanged.__doc__)
    print(unicode(SampleInterface.GetLastInput), repr(SampleInterface.GetLastInput), dir(SampleInterface.GetLastInput))
    print(SampleInterface.GetLastInput.__doc__)


if __name__ == '__main__':
    test()
