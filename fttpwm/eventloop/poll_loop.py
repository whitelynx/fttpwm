"""Polling socket event loop

"""
import heapq
import logging
import select
import sys
import time

from .base import BaseEventLoop, StreamEvents


logger = logging.getLogger("fttpwm.eventloop.zmq_loop")


streamEventsToPollEvents = {
        StreamEvents.INCOMING: select.POLLIN,
        StreamEvents.OUTGOING: select.POLLOUT,
        }


class PollEventLoop(BaseEventLoop):
    def __init__(self):
        super(PollEventLoop, self).__init__()

        self.running = False
        self.handlers = dict()
        self.timers = []
        self.idleCallbacks = list()

        # select.poll won't work on Windows, but at the moment I don't particularly care. This can be implemented with
        # select.select later if someone wants it.
        self.poll = select.poll()

    def callAt(self, deadline, callback):
        """Call the given `callback` at the time given by `deadline`.

        `deadline` should be in seconds since the Epoch (a UNIX timestamp), in local time.

        """
        heapq.heappush(self.timers, (deadline, callback))

    def callAfter(self, delay, callback):
        """Call the given `callback` after `delay` seconds.

        """
        self.callAt(time.time() + self.asTimedelta(delay).total_seconds(), callback)

    def callWhenIdle(self, callback):
        """Call the given `callback` the next time there are no waiting events.

        """
        self.idleCallbacks.append(callback)

    @property
    def timeToNextTimer(self):
        return self.timers[0] - time.time()

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

        key = fd, streamEventsToPollEvents[event]
        self.poll.register(*key)
        self.handlers[key] = lambda fd, evt: handler(stream, evt)

    def missingHandler(self, fd, evt):
        logger.error("Couldn't find handler for event %r on descriptor %r!", evt, fd)

    def doPoll(self, timeoutMS):
        wakeups = self.poll.poll(timeoutMS)

        for fd, evt in wakeups:
            self.handlers.get((fd, evt), self.missingHandler)(fd, evt)

        if len(wakeups) == 0:
            # No waiting events; run all the callbacks in idleCallbacks, and clear it.
            callbacks = self.idleCallbacks
            self.idleCallbacks = list()
            for callback in callbacks:
                callback()

    def isRunning(self):
        """Check whether the event loop is currently running.

        """
        return self.running

    def exit(self):
        """Exit the event loop.

        Calling this will cause run() to return after this iteration.

        """
        self.running = False

    def run(self):
        """Start the event loop.

        This should not return until the program exits.

        """
        logger.info("Starting main event loop.")
        self.running = True

        try:
            while self.running:
                # Poll for events until the next timer is due.
                timeoutMS = int(self.timeToNextTimer / 1000)
                self.doPoll(timeoutMS)

                # Process all timers that have reached their deadline.
                while self.timers[0][0] < time.time():
                    deadline, callback = heapq.heappop(self.timers)
                    callback()

                # Check to see if we're idle.
                self.doPoll(0)

        except Exception:
            logger.exception("Error in main event loop! Exiting with error status.")
            sys.exit(1)

        logger.info("Event loop terminated; shutting down normally.")
