# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function
"""FTTPWM: D-Bus interface definition classes

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from weakref import ref


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
    class _DBusInterface(object):
        __doc__ = """D-Bus interface base class for the {} interface

        """.format(interfaceName)
        _dbus_interfaceName = interfaceName

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

    return _DBusInterface


class _LocalInterfaceMethodInfo(object):
    """D-Bus interface method information, for wrapping local implementation methods.

    """
    def __init__(self, interfaceMethod, wrapped):
        self.interfaceMethod = interfaceMethod
        self.wrapped = wrapped

    def __call__(self, *args, **kwargs):
        """Call the wrapped method.

        """
        return self.wrapped(*args, **kwargs)


class _RemoteInterfaceMethodInfo(object):
    """D-Bus interface method information, for wrapping methods on remote objects.

    """
    def __init__(self, interfaceMethod, obj):
        self.interfaceMethod = interfaceMethod
        self.obj = obj

    def __call__(self, *args, **kwargs):
        """Call this method on the remote object.

        In addition to the arguments accepted by the remote method, the following keyword-only argument is accepted:
        - `dbus_destination`: Tells the bus to only send the method call to the given connection

        @returns a new `fttpwm.dbus.connection.Callbacks` object for this method call

        """
        destination = kwargs.pop('dbus_destination', None)

        if len(kwargs) > 0:
            raise NotImplementedError("Calling methods with explicit keyword arguments is not yet supported!")

        self.obj._dbus_bus.callMethod(
                self.obj._dbus_path,
                self.interfaceMethod.methodName,
                inSignature=self.interfaceMethod.inSignature,
                args=args,
                interface=self.interfaceMethod.interfaceName,
                destination=destination
                )


class _InterfaceMethod(object):
    """D-Bus interface method class

    """
    def __init__(self, func, inSig='', outSig='', resultFields=None):
        self.methodName = func.__name__
        self.__doc__ = func.__doc__
        self.interface = None
        self.interfaceName = None

        self.inSignature = inSig
        self.outSignature = outSig

        self.resultFields = resultFields
        if isinstance(resultFields, basestring):
            self.resultFields = resultFields.split()

    def __get__(self, instance, owner):
        self.interface = ref(owner)
        self.interfaceName = owner._dbus_interfaceName
        return self

    def __unicode__(self):
        return u'{}.{}'.format(self.interfaceName, self.methodName)

    def __call__(self, func):
        return _LocalInterfaceMethodInfo(self, func)


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


class _LocalSignalWrapper(object):
    def __init__(self, signal, preEmit):
        self.signal = signal
        self.obj = None
        self.preEmit = preEmit

    @property
    def interface(self):
        return self.signal.interface

    @property
    def interfaceName(self):
        return self.signal.interfaceName

    def __get__(self, instance, owner):
        self.obj = instance
        return self

    def __call__(self, *args, **kwargs):
        """Emit this signal from the object it is attached to.

        The `SIGNAL` message will have its `PATH` set to the path of `obj`, its `INTERFACE` set to the name of the
        interface in which this signal was defined, and `MEMBER` set to the signal's name.

        """
        if self.preEmit is not None:
            self.preEmit(*args, **kwargs)

        #FIXME: Implement!


class _InterfaceSignal(object):
    """D-Bus interface signal class

    """
    def __init__(self, func, sig=''):
        self.signalName = func.__name__
        self.__doc__ = func.__doc__
        self.interface = None
        self.interfaceName = None

        self.signature = sig

    def __get__(self, instance, owner):
        self.interface = ref(owner)
        self.interfaceName = owner._dbus_interfaceName
        return self

    def __unicode__(self):
        return u'{}.{}'.format(self.interfaceName, self.signalName)

    def __call__(self, preEmit=None):
        wrapper = _LocalSignalWrapper(self, preEmit)
        wrapper.__name__ = '{}'.format(self.signalName)
        wrapper.__doc__ = self.__doc__
        return wrapper


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
