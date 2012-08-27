# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: D-Bus introspection example

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import logging

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import Terminal256Formatter

from fttpwm import logconfig


logconfig.configure()

logger = logging.getLogger("fttpwm.examples.introspection")


from fttpwm.dbus.bus import SessionBus

try:
    from fttpwm.eventloop.zmq_loop import ZMQEventLoop

    eventloop = ZMQEventLoop()
    logger.info("Using the ZeroMQ event loop.")

except ImportError:
    logger.warn("Couldn't import ZeroMQ event loop! Falling back to polling event loop.", exc_info=True)

    from fttpwm.eventloop.poll_loop import PollEventLoop

    eventloop = PollEventLoop()


bus = None


def connect():
    global bus, server
    print("\033[1;42;38;5;16mconnect\033[m")
    SessionBus.machineID = '07b6ac7a4c79d9b9628392f30000bea1'
    bus = SessionBus()
    bus.identified.connect(onIdentified)


def onIdentified():
    global gotResponse
    print("\033[1;43;38;5;16monIdentified\033[m")
    sendIntrospect()


def sendIntrospect():
    global bus
    print("\033[1;46;38;5;16mIntrospect\033[m")
    cb = bus.Introspect()
    cb.onReturn = onIntrospectReturn


def onIntrospectReturn(response):
    print("\033[48;5;17mIntrospection of {}:\033[m".format(bus.dbus_path))
    print(highlight(response.body[0], get_lexer_by_name('xml'), Terminal256Formatter()))
    eventloop.exit()


eventloop.callWhenIdle(connect)
eventloop.run()
