# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: HistoryStack class

Copyright (c) 2013 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import collections

from .orderedsets import OrderedWeakSet


class HistoryStack(OrderedWeakSet, collections.Sequence):
    """An ordered weakref set which moves items to the beginning of the set each time they're added, even if already
    contained.

    """
    def add(self, value):
        self.discard(value)
        super(HistoryStack, self).add(value)

    def __iter__(self):
        # We deal with our items in reverse order, since OrderedSet always puts new items at the end of the set instead
        # of the beginning.
        return reversed(list(super(HistoryStack, self).__iter__()))

    def __getitem__(self, idx):
        it = iter(self)
        item = None

        for idx in range(idx):
            try:
                item = it.next()
            except StopIteration:
                raise IndexError("HistoryStack index out of range", idx)

        return item
