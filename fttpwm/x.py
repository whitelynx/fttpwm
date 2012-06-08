# -*- codin-g: utf-8 -*-
"""FTTPWM: X connection utilities

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from collections import deque
import datetime
import logging
import os
import select
import sys

import xcb
from xcb.xproto import Atom, CW, ConfigWindow, EventMask, InputFocus, PropMode, SetMode, StackMode, WindowClass
from xcb.xproto import CirculateRequestEvent, ConfigureRequestEvent, MapRequestEvent
from xcb.xproto import ConfigureNotifyEvent, MappingNotifyEvent

import xpybutil
import xpybutil.event
import xpybutil.ewmh as ewmh
from xpybutil.util import get_atom as atom
import xpybutil.window

from .ewmh import EWMHAction, EWMHWindowState, EWMHWindowType
from .settings import settings
from .setroot import setWallpaper
from .utils import convertAttributes, findCurrentVisual
from .xevents import SelectionNotifyEvent
from .frame import WindowFrame
from .signals import Signal
from .signaled import SignaledDict
from .statusbar import StatusBar
from .workspace import WorkspaceManager
from . import singletons


logger = logging.getLogger("fttpwm.wm")

settings.setDefaults(
        autostart=[]
        )


class Color(object):
    @staticmethod
    def float(*components):
        return map(lambda x: int(x * 2 ** 16), components)


class XConnection(object):
    class RecurringEvent(object):
        def __init__(self, interval, callback):
            self.interval, self.callback = interval, callback
            self.nextCall = datetime.datetime.now() + interval

        def check(self):
            try:
                if datetime.datetime.now() > self.nextCall:
                    self()
            except StopIteration:
                # Leave the timer queue.
                return None

            # Stay in the timer queue.
            return self

        def __call__(self):
            self.callback()
            self.nextCall = datetime.datetime.now() + self.interval

    def __init__(self):
        self.pid = os.getpid()

        self.startupFinished = False
        self.onStartup = Signal()
        self.timers = deque()
        self.whenQueueEmpty = set()

        assert singletons.x is None
        singletons.x = self

        self.setup = xpybutil.conn.get_setup()
        self.screenNumber = xpybutil.conn.pref_screen
        self.screen = self.setup.roots[self.screenNumber]
        self.root = self.screen.root
        self.depth = self.screen.root_depth
        self.visualID = self.screen.root_visual
        self.visual = findCurrentVisual(self.screen, self.depth, self.visualID)
        self.screenWidth = self.screen.width_in_pixels
        self.screenHeight = self.screen.height_in_pixels
        self.colormap = self.screen.default_colormap

        self.white = self.screen.white_pixel
        self.black = self.screen.black_pixel

    def allocColor(self, color):
        """Allocate the given color and return its XID.

        `color` must be a tuple `(r, g, b)` where `r`, `g`, and `b` are between 0 and 1.

        """
        return xpybutil.conn.core.AllocColor(self.colormap, *color).reply().pixel

    def createWindow(self, x, y, width, height, attributes={}, windowID=None, parentID=None, borderWidth=0,
            windowClass=WindowClass.InputOutput, checked=False):
        """A convenience method to create a new window.

        The major advantage of this is the ability to use a dictionary to specify window attributes; this eliminates
        the need to figure out what order to specify values in according to the numeric values of the 'CW' or
        'ConfigWindow' enum members you're using.

        """
        if windowID is None:
            windowID = xpybutil.conn.generate_id()

        if parentID is None:
            parentID = self.root

        attribMask = 0
        attribValues = list()

        # Values must be sorted by CW or ConfigWindow enum value, ascending.
        # Luckily, the tuples we get from dict.iteritems will automatically sort correctly.
        for attrib, value in sorted(attributes.iteritems()):
            attribMask |= attrib
            attribValues.append(value)

        if checked:
            call = xpybutil.conn.core.CreateWindowChecked
        else:
            call = xpybutil.conn.core.CreateWindow

        cookie = call(
                self.depth,
                windowID, parentID,
                x, y, width, height,
                borderWidth, windowClass,
                self.visualID,
                attribMask, attribValues
                )

        if checked:
            return windowID, cookie
        else:
            return windowID

    def callEvery(self, interval, callback):
        self.timers.append(self.RecurringEvent(interval, callback))

    def callWhenQueueEmpty(self, callback):
        self.whenQueueEmpty.add(callback)

    def exit(self):
        self.running = False

    ## Main event loop ####
    def run(self):
        logger.info("Starting main event loop.")
        self.running = True

        # select.poll won't work on Windows, but at the moment I don't particularly care. This can be implemented with
        # select.select later if someone wants it.
        fdPoll = select.poll()
        # Poll the X connection's file descriptor for incoming data.
        fdPoll.register(xpybutil.conn.get_file_descriptor(), select.POLLIN)

        #NOTE: This does several things that xpybutil.event.main doesn't do:
        # - It ensures that the WM gets MapRequest events, and windows get SelectionRequest when appropriate.
        # - It implements crude timers so various things can register a callback to happen every `n` seconds, or once
        #   after `n` seconds.
        # - It implements callWhenQueueEmpty, which effectively runs a callback when we're idle.
        try:
            while self.running:
                #FIXME: Find a better way to do timeouts than polling and sleeping! It'd be preferable to block, if we
                # could set a timeout on the blocking call.
                #xpybutil.event.read(block=True)
                xpybutil.event.read(block=False)

                # Check if there are any waiting events.
                if len(xpybutil.event.peek()) == 0:
                    # Run all the callbacks in whenQueueEmpty, and clear it.
                    for callback in self.whenQueueEmpty:
                        callback()

                    self.whenQueueEmpty.clear()

                    # Poll for events for 10ms, then time out so we can check our timers.
                    fdPoll.poll(10)

                for e in xpybutil.event.queue():
                    w = None
                    if isinstance(e, MappingNotifyEvent):
                        # MappingNotify events get sent to the xpybutil.keybind.update_keyboard_mapping function, to
                        # update the stored keyboard mapping.
                        w = None
                    elif isinstance(e, (CirculateRequestEvent, ConfigureRequestEvent, MapRequestEvent)):
                        # Send all SubstructureRedirect *Request events to the parent window, which should be the
                        # window which had the SubstructureRedirect mask set on it. (that is, if i'm reading the docs
                        # correctly)
                        w = e.parent
                    elif hasattr(e, 'event'):
                        w = e.event
                    elif hasattr(e, 'window'):
                        w = e.window
                    elif hasattr(e, 'owner'):
                        w = e.owner
                    elif hasattr(e, 'requestor'):
                        w = e.requestor

                    key = (e.__class__, w)
                    for cb in getattr(xpybutil.event, '__callbacks').get(key, []):
                        try:
                            cb(e)
                        except Exception:
                            logger.exception("Error while calling callback %r for %r event on %r! Continuing...",
                                    cb, e.__class__, w)

                    #XXX: Debugging...
                    #if isinstance(e, ConfigureNotifyEvent):
                    #    logger.debug("Got ConfigureNotifyEvent: %r; w=%r; listeners: %r",
                    #            e.__dict__, w, getattr(xpybutil.event, '__callbacks').get(key, []))
                    #if isinstance(e, MapRequestEvent):
                    #    logger.debug("Got MapRequestEvent: %r; w=%r; listeners: %r",
                    #            e.__dict__, w, getattr(xpybutil.event, '__callbacks').get(key, []))

                xpybutil.conn.flush()

                for timer in self.timers:
                    # If the timer's 'check' method returns None, remove it from the queue.
                    if timer.check() is None:
                        self.timers.remove(timer)

        except xcb.Exception:
            logger.exception("Error in main event loop! Exiting with error status.")
            sys.exit(1)

        logger.info("Event loop terminated; shutting down normally.")
