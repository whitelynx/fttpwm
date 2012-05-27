# -*- coding: utf-8 -*-
"""FTTPWM: Main application

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from collections import OrderedDict
from functools import update_wrapper

from .signals import Signal


class _UpdateAction(object):
    def __init__(action, name):
        action.name = name

    class _InnerUpdateAction(object):
        def __init__(inner, obj, wrapped):
            inner.obj = obj
            inner.wrapped = wrapped

        def __call__(inner, *args, **kwargs):
            retval = inner.wrapped(*args, **kwargs)
            inner.obj.updated()
            return retval

    def __get__(action, obj, objtype=None):
        wrapped = getattr(super(objtype, obj), action.name)
        wrapper = _UpdateAction._InnerUpdateAction(obj, wrapped)

        if hasattr(wrapped, '__module__'):
            update_wrapper(wrapper, wrapped)
        else:
            update_wrapper(wrapper, wrapped, assigned=('__name__', '__doc__'))

        return wrapper


#TODO: SignaledProperty!


class SignaledList(list):
    def __init__(self, *args, **kwargs):
        super(SignaledList, self).__init__(*args, **kwargs)
        self.updated = Signal()

    __delitem__ = _UpdateAction('__delitem__')
    __delslice__ = _UpdateAction('__delslice__')
    __iadd__ = _UpdateAction('__iadd__')
    __imul__ = _UpdateAction('__imul__')
    __setitem__ = _UpdateAction('__setitem__')
    __setslice__ = _UpdateAction('__setslice__')
    append = _UpdateAction('append')
    extend = _UpdateAction('extend')
    insert = _UpdateAction('insert')
    pop = _UpdateAction('pop')
    remove = _UpdateAction('remove')
    reverse = _UpdateAction('reverse')
    sort = _UpdateAction('sort')


class SignaledDict(dict):
    def __init__(self, *args, **kwargs):
        super(SignaledDict, self).__init__(*args, **kwargs)
        self.updated = Signal()

    __delitem__ = _UpdateAction('__delitem__')
    __setitem__ = _UpdateAction('__setitem__')
    clear = _UpdateAction('clear')
    pop = _UpdateAction('pop')
    popitem = _UpdateAction('popitem')
    setdefault = _UpdateAction('setdefault')
    update = _UpdateAction('update')


class SignaledOrderedDict(OrderedDict):
    def __init__(self, *args, **kwargs):
        super(SignaledOrderedDict, self).__init__(*args, **kwargs)
        self.updated = Signal()

    __delitem__ = _UpdateAction('__delitem__')
    __setitem__ = _UpdateAction('__setitem__')
    clear = _UpdateAction('clear')
    pop = _UpdateAction('pop')
    popitem = _UpdateAction('popitem')
    setdefault = _UpdateAction('setdefault')
    update = _UpdateAction('update')
