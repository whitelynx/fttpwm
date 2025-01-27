""" A signal/slot implementation

File:    signal.py
Author:  Thiago Marcos P. Santos
Author:  Christopher S. Case
Author:  David H. Bronke
Created: August 28, 2008
Updated: December 12, 2011
License: MIT

"""
import inspect
import logging
import traceback

try:
    # location in Python 2.7 and 3.1
    from weakref import WeakSet
except ImportError:
    # separately installed
    from compat.weakrefset import WeakSet

from weakref import WeakKeyDictionary


logger = logging.getLogger("fttpwm.signals")


class Signal(object):
    def __init__(self):
        self._functions = WeakSet()
        self._methods = WeakKeyDictionary()

    def __call__(self, *args, **kargs):
        # Call handler functions
        for func in list(self._functions):
            try:
                func(*args, **kargs)

            except Exception, ex:
                if isinstance(ex, SystemExit):
                    raise
                logger.exception("Got exception while calling signal handler %r!", func)
                logger.debug("".join(["Called from:\n"] + traceback.format_stack()))

        # Call handler methods
        for obj, funcs in self._methods.items():
            for func in list(funcs):
                try:
                    func(obj, *args, **kargs)

                except Exception, ex:
                    if isinstance(ex, SystemExit):
                        raise
                    logger.exception("Got exception while calling signal handler %r from object %r!", func, obj)
                    logger.debug("".join(["Called from:\n"] + traceback.format_stack()))

    def connect(self, slot):
        if inspect.ismethod(slot):
            # Python 2.5 support
            try:
                slot_self = slot.__self__
            except AttributeError:
                slot_self = slot.im_self

            try:
                slot_func = slot.__func__
            except AttributeError:
                slot_func = slot.im_func

            if slot_self not in self._methods:
                self._methods[slot_self] = set()

            self._methods[slot_self].add(slot_func)

        else:
            self._functions.add(slot)

    def disconnect(self, slot):
        if inspect.ismethod(slot):
            # Python 2.5 support
            try:
                slot_self = slot.__self__
            except AttributeError:
                slot_self = slot.im_self

            try:
                slot_func = slot.__func__
            except AttributeError:
                slot_func = slot.im_func

            if slot_self in self._methods:
                self._methods[slot_self].remove(slot_func)
        else:
            if slot in self._functions:
                self._functions.remove(slot)

    def clear(self):
        self._functions.clear()
        self._methods.clear()


# Sample usage:
if __name__ == '__main__':
    class Model(object):
        def __init__(self, value):
            self.__value = value
            self.changed = Signal()

        def set_value(self, value):
            self.__value = value
            self.changed()  # Emit signal

        def get_value(self):
            return self.__value

    class View(object):
        def __init__(self, model):
            self.model = model
            model.changed.connect(self.model_changed)

        def model_changed(self):
            print("   New value:", self.model.get_value())

    print("Beginning Tests:")
    model = Model(10)
    view1 = View(model)
    view2 = View(model)
    view3 = View(model)

    print("Setting value to 20...")
    model.set_value(20)

    print("Deleting a view, and setting value to 30...")
    del view1
    model.set_value(30)

    print("Clearing all listeners, and setting value to 40...")
    model.changed.clear()
    model.set_value(40)

    print("Testing non-member function...")

    def bar():
        print("   Calling Non Class Function!")

    model.changed.connect(bar)
    model.set_value(50)
