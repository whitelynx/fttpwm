# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: D-Bus interface definition classes

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""


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

    return _DBusInterface


class _InterfaceMethod(object):
    """D-Bus interface method class

    """
    def __init__(self, func, inSig='', outSig='', resultFields=None):
        self.methodName = func.__name__
        self.__doc__ = func.__doc__
        self.interfaceName = None

        self.inSignature = inSig
        self.outSignature = outSig

        self.resultFields = resultFields
        if isinstance(resultFields, basestring):
            self.resultFields = resultFields.split()

    def __get__(self, instance, owner):
        self.interfaceName = owner._dbus_interfaceName
        return self

    def __unicode__(self):
        return u'{}.{}'.format(self.interfaceName, self.methodName)

    def __call__(self, func):
        raise NotImplementedError


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


class _InterfaceSignal(object):
    """D-Bus interface signal class

    """
    def __init__(self, func, sig=''):
        self.signalName = func.__name__
        self.__doc__ = func.__doc__
        self.interfaceName = None

        self.signature = sig

    def __get__(self, instance, owner):
        self.interfaceName = owner._dbus_interfaceName
        return self

    def __unicode__(self):
        return u'{}.{}'.format(self.interfaceName, self.signalName)

    def __call__(self, func):
        raise NotImplementedError


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


if __name__ == '__main__':
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

    print unicode(SampleInterface), repr(SampleInterface), dir(SampleInterface)
    print SampleInterface.__doc__
    print unicode(SampleInterface.LastInputChanged), repr(SampleInterface.LastInputChanged), dir(SampleInterface.LastInputChanged)
    print SampleInterface.LastInputChanged.__doc__
    print unicode(SampleInterface.GetLastInput), repr(SampleInterface.GetLastInput), dir(SampleInterface.GetLastInput)
    print SampleInterface.GetLastInput.__doc__
