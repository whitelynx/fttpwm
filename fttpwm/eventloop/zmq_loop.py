"""0MQ event loop

"""
import logging
from datetime import timedelta

import errno
import functools
import socket

import zmq
import zmq.eventloop.ioloop

from .base import BaseEventLoop, StreamEvents


logger = logging.getLogger("fttpwm.eventloop.zmq_loop")


ioLoopEventsToPollEvents = {
        StreamEvents.INCOMING: zmq.eventloop.ioloop.IOLoop.READ,
        StreamEvents.OUTGOING: zmq.eventloop.ioloop.IOLoop.WRITE,
        }


class ZMQEventLoop(BaseEventLoop):
    def __init__(self):
        super(ZMQEventLoop, self).__init__()
        self.io_loop = zmq.eventloop.ioloop.IOLoop.instance()

    def callAt(self, deadline, callback):
        """Call the given `callback` at the time given by `deadline`.

        `deadline` should be in seconds since the Epoch (a UNIX timestamp), in local time.

        """
        return self.io_loop.add_timeout(deadline, callback)

    def callAfter(self, delay, callback):
        """Call the given `callback` after `delay` seconds.

        """
        return self.io_loop.add_timeout(self.asTimedelta(delay), callback)

    def callWhenIdle(self, callback):
        """Call the given `callback` the next time there are no waiting events.

        """
        self.io_loop.add_callback(callback)

    def callEvery(self, interval, callback):
        """Call the given `callback` once every `interval`.

        `interval` should either be a `datetime.timedelta`, or a number representing seconds.

        """
        cb = None

        def call():
            if not callback():
                cb.stop()

        cb = zmq.eventloop.ioloop.PeriodicCallback(
                call,
                self.asTimedelta(interval).total_seconds() * 1000,
                self.io_loop
                )
        cb.start()

    def register(self, stream, handler, event=StreamEvents.INCOMING):
        """Register a `handler` for a given `event` on the given `stream`.

        `handler` will be called with `stream` and `event` as arguments.

        """
        # This should cover most cases.
        try:
            fd = stream.fileno()
        except TypeError:
            fd = stream.fileno
        except AttributeError:
            # Stupid xpyb not conforming to the file-like object protocol.
            fd = stream.get_file_descriptor()

        self.io_loop.add_handler(fd, lambda fd, evt: handler(stream, evt), ioLoopEventsToPollEvents[event])

    def isRunning(self):
        """Check whether the event loop is currently running.

        """
        self.io_loop.running()

    def exit(self):
        """Exit the event loop.

        Calling this will cause run() to return after this iteration.

        """
        self.io_loop.stop()

    def run(self):
        """Start the event loop.

        This should not return until the program exits.

        """
        self.io_loop.start()
