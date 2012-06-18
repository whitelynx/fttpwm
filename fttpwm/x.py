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


class XConnection(object):
    def __init__(self):
        self.startupFinished = False
        self.onStartup = Signal()
        self.timers = deque()
        self.whenQueueEmpty = set()

        assert singletons.x is None
        singletons.x = self

        self.conn = xpybutil.conn

        self.setup = self.conn.get_setup()
        self.screenNumber = self.conn.pref_screen
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

        singletons.eventloop.register(self.conn, self.handleXCBComm)

    def __getattr__(self, name):
        """Get an attribute from the X connection.

        Simplifies things so you don't have to do `singletons.x.conn.core.func()`; instead, you just call
        `singletons.x.core.func()`.

        """
        return getattr(self.conn, name)

    def allocColor(self, color):
        """Allocate the given color and return its XID.

        `color` must be a tuple `(r, g, b)` where `r`, `g`, and `b` are between 0 and 1.

        """
        return self.conn.core.AllocColor(self.colormap, *color).reply().pixel

    def createWindow(self, x, y, width, height, attributes={}, windowID=None, parentID=None, borderWidth=0,
            windowClass=WindowClass.InputOutput, checked=False):
        """A convenience method to create a new window.

        The major advantage of this is the ability to use a dictionary to specify window attributes; this eliminates
        the need to figure out what order to specify values in according to the numeric values of the 'CW' or
        'ConfigWindow' enum members you're using.

        """
        if windowID is None:
            windowID = self.conn.generate_id()

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
            call = self.conn.core.CreateWindowChecked
        else:
            call = self.conn.core.CreateWindow

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

    def setProperty(self, windowID, property, data, type=Atom.STRING, format=8, mode=PropMode.Replace, data_len=None):
        if data_len is None:
            try:
                data_len = len(data)
            except:
                data_len = 1

        #TODO: Take care of some of the needed struct.pack() magic here?

        xpybutil.conn.core.ChangeProperty(mode, windowID, property, type, format, data_len, data)

    def printXCBExc(self, error):
        logger.exception("Protocol error %s received!", error.__class__.__name__)

        # These attributes seem to be completely undocumented, and they don't show up in dir(error) because they're
        # dynamic.
        logger.debug("""Error details:
    Error code: %r
    Response type: %r
    Sequence num: %r
    Raw msg: %s""",
                error.message.code,
                error.message.response_type,
                error.message.sequence,
                ' '.join('{:02X}'.format(ord(c)) for c in error.message)
                )

    def handleXCBComm(self, stream, evt):
        """Read all incoming data from the X server, and process all resulting events.

        """
        #NOTE: This does several things that xpybutil.event.main doesn't do:
        # - ensures that the WM gets MapRequest events
        # - ensures that windows get SelectionRequest when appropriate
        try:
            try:
                xpybutil.event.read(block=False)
            except xcb.ProtocolException, error:
                self.printXCBExc(error)

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

            self.conn.flush()

        except xcb.Exception:
            logger.exception("Error while handling X11 communication!")
