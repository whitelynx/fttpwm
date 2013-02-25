"""Ordered set and ordered weak reference set classes from http://stackoverflow.com/a/7829569/677694

Code by Raymond Hettinger, licensed under the Creative Commons Attribution-ShareAlike 3.0 Unported license;
see http://creativecommons.org/licenses/by-sa/3.0/ for details.

"""
import collections
import weakref


class OrderedSet(collections.MutableSet):
    def __init__(self, values=()):
        self._od = collections.OrderedDict().fromkeys(values)

    def __len__(self):
        return len(self._od)

    def __iter__(self):
        return iter(self._od)

    def __contains__(self, value):
        return value in self._od

    def add(self, value):
        self._od[value] = None

    def discard(self, value):
        self._od.pop(value, None)


class OrderedWeakSet(weakref.WeakSet):
    def __init__(self, values=()):
        super(OrderedWeakSet, self).__init__()
        self.data = OrderedSet()
        for elem in values:
            self.add(elem)
