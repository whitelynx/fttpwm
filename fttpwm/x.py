# -*- coding: utf-8 -*-
"""FTTPWM: X connection utilities

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from collections import deque
import logging

import xcb
from xcb.xproto import Atom, Mapping, PropMode
from xcb.xproto import WindowClass
from xcb.xproto import CirculateRequestEvent, ConfigureRequestEvent, MapRequestEvent
from xcb.xproto import MappingNotifyEvent

import xpybutil
import xpybutil.event
import xpybutil.util
import xpybutil.window

from .settings import settings
from .utils.x import findCurrentVisual
from .signals import Signal
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

        self.pendingUpdateKeyboardMapping = None
        self.pendingUpdateModifierMapping = None

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

    def getProperty(self, windowID, property, type=xcb.xproto.GetPropertyType.Any, delete=False, data_offset=None,
            data_len=None, cb=None):

        data_offset = 0 if data_offset is None else data_offset
        data_len = (2 ** 32 - 1) if data_len is None else data_len

        if isinstance(property, basestring):
            property = xpybutil.util.get_atom(property)

        cookie = xpybutil.conn.core.GetProperty(delete, windowID, property, type, data_offset, data_len)

        if cb:
            def handleReply():
                error = None
                value = None

                try:
                    value = xpybutil.util.get_property_value(cookie.reply())
                except Exception as ex:
                    error = ex

                cb(value, error)

            singletons.eventloop.callWhenIdle(handleReply)

        else:
            # If no callback was passed in, block until we get a reply, then return it.
            return xpybutil.util.get_property_value(cookie.reply())

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

    def updateKeyboardMapping(self):
        logger.debug("Keyboard mapping changed; updating xpybutil bindings...")
        try:
            xpybutil.keybind.update_keyboard_mapping(self.pendingUpdateKeyboardMapping)
            self.pendingUpdateKeyboardMapping = None
        except:
            logger.exception("Exception while updating xpybutil bindings for new keyboard mapping!")

    def updateModifierMapping(self):
        logger.debug("Modifier mapping changed; updating xpybutil bindings...")
        try:
            xpybutil.keybind.update_keyboard_mapping(self.pendingUpdateModifierMapping)
            self.pendingUpdateModifierMapping = None
        except:
            logger.exception("Exception while updating xpybutil bindings for new modifier mapping!")

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

                    if e.request == Mapping.Keyboard:
                        logger.info("Got MappingNotifyEvent with request=Keyboard; queueing updateKeyboardMapping().")
                        if self.pendingUpdateKeyboardMapping is None:
                            singletons.eventloop.callWhenIdle(self.updateKeyboardMapping)
                        self.pendingUpdateKeyboardMapping = e

                    elif e.request == Mapping.Modifier:
                        logger.info("Got MappingNotifyEvent with request=Modifier; queueing updateModifierMapping().")
                        if self.pendingUpdateModifierMapping is None:
                            singletons.eventloop.callWhenIdle(self.updateModifierMapping)
                        self.pendingUpdateModifierMapping = e

                    # Don't process this event right now; wait for the queue to empty first.
                    continue

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
                #logger.debug("Calling callbacks for %r event on window %r...", *key)
                for cb in getattr(xpybutil.event, '__callbacks').get(key, []):
                    #logger.debug("  Calling callback %r...", cb)
                    try:
                        cb(e)
                    except Exception:
                        logger.exception("Error while calling callback %r for %r event on %r! Continuing...",
                                cb, e.__class__, w)
                    #logger.debug("  Callback %r finished.", cb)
                #logger.debug("Finished calling callbacks for %r event on window %r.", *key)

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
