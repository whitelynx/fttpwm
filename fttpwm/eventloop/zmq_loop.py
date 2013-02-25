"""0MQ event loop

"""
import logging
import warnings

import zmq
import zmq.eventloop.ioloop

from .base import BaseEventLoop, StreamEvents


logger = logging.getLogger("fttpwm.eventloop.zmq_loop")


streamEventsToZMQEvents = {
        StreamEvents.INCOMING: zmq.eventloop.ioloop.IOLoop.READ,
        StreamEvents.OUTGOING: zmq.eventloop.ioloop.IOLoop.WRITE,
        }


class ZMQEventLoop(BaseEventLoop):
    def __init__(self):
        super(ZMQEventLoop, self).__init__()
        self.io_loop = zmq.eventloop.ioloop.IOLoop.instance()
        self.idleCallbacks = set()

    def callAt(self, deadline, callback):
        """Call the given `callback` at the time given by `deadline`.

        `deadline` should be in seconds since the Epoch (a UNIX timestamp), in local time.

        """
        return self.io_loop.add_timeout(deadline, callback)

    def callAfter(self, delay, callback):
        """Call the given `callback` after `delay` seconds.

        """
        return self.io_loop.add_timeout(self.asTimedelta(delay), callback)

    def callWhenIdle(self, callback, allowDuplicates=False):
        """Call the given `callback` the next time there are no waiting events.

        """
        if allowDuplicates:
            self.io_loop.add_callback(callback)
        else:
            def callCB():
                self.idleCallbacks.discard(callback)
                callback()

            self.idleCallbacks.add(callback)
            self.io_loop.add_callback(callCB)

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

    def register(self, stream, handler, events=(StreamEvents.INCOMING, ), event=None):
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

        if event is not None:
            warnings.warn("'event' is deprecated! Use 'events' instead.", DeprecationWarning)
            events = [event]

        events = sum(streamEventsToZMQEvents[event] for event in events)

        def callHandler(fd, evt):
            for streamEvt, zmqEvt in streamEventsToZMQEvents.iteritems():
                if evt & zmqEvt:
                    handler(stream, streamEvt)

        self.io_loop.add_handler(fd, callHandler, events)

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
