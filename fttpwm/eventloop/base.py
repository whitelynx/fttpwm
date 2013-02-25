"""Base event loop

"""
from abc import ABCMeta, abstractmethod
import datetime
import logging
import numbers

from .. import singletons


logger = logging.getLogger("fttpwm.eventloop.base")


class StreamEvents(object):
    INCOMING = 0
    OUTGOING = 1


class BaseEventLoop(object):
    __metaclass__ = ABCMeta

    class RecurringCallback(object):
        def __init__(self, eventloop, interval, callback):
            self.eventloop = eventloop
            self.interval = interval
            self.callback = callback

        def __call__(self, *args, **kwargs):
            if self.callback(*args, **kwargs):
                self.callAfter(self.interval, self)

    def __init__(self):
        if singletons.eventloop is None:
            singletons.eventloop = self

    @abstractmethod
    def callAt(self, deadline, callback):
        """Call the given `callback` at the time given by `deadline`.

        `deadline` should be in seconds since the Epoch (a UNIX timestamp), in local time.

        """

    @abstractmethod
    def callAfter(self, delay, callback):
        """Call the given `callback` after `delay` seconds.

        `delay` should either be a `datetime.timedelta`, or a number representing seconds.

        """

    def callEvery(self, interval, callback):
        """Call the given `callback` once every `interval`.

        `interval` should either be a `datetime.timedelta`, or a number representing seconds.

        """
        cb = self.RecurringCallback(self, interval, callback)
        self.callAfter(interval, cb)

    @abstractmethod
    def callWhenIdle(self, callback, allowDuplicates=False):
        """Call the given `callback` the next time there are no waiting events.

        """

    @abstractmethod
    def register(self, stream, handler, event=StreamEvents.INCOMING):
        """Register a `handler` for a given `event` on the given `stream`.

        `handler` will be called with `stream` and `event` as arguments.

        """

    @abstractmethod
    def isRunning(self):
        """Check whether the event loop is currently running.

        """

    @abstractmethod
    def exit(self):
        """Exit the event loop.

        Calling this will cause run() to return after this iteration.

        """

    @abstractmethod
    def run(self):
        """Start the event loop.

        This should not return until the program exits.

        """

    @staticmethod
    def asTimedelta(interval):
        """Convert `interval` to a `datetime.timedelta` if needed.

        `interval` should either be a `datetime.timedelta`, or a number representing seconds.

        """
        if isinstance(interval, datetime.timedelta):
            return interval

        elif isinstance(interval, numbers.Real):
            return datetime.timedelta(seconds=interval)

        raise TypeError
