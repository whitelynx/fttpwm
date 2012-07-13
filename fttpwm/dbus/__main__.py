# -*- cod-ing: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: D-Bus client test

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import logging

from .. import logconfig

from . import connection


logconfig.configure()

logger = logging.getLogger("fttpwm.dbus.__main__")


try:
    from ..eventloop.zmq_loop import ZMQEventLoop

    eventloop = ZMQEventLoop()
    logger.info("Using the ZeroMQ event loop.")

except ImportError:
    logger.warn("Couldn't import zmq! Falling back to polling event loop.", exc_info=True)

    from .eventloop.poll_loop import PollEventLoop

    eventloop = PollEventLoop()


bus = None

gotResponse = False


def connect():
    global bus
    print("\033[1;90;42mconnect\033[m")
    bus = connection.SessionBus()
    bus.identified.connect(onIdentified)


def onIdentified():
    global gotResponse
    print("\033[1;90;43monIdentified\033[m")
    gotResponse = False
    eventloop.callEvery(0.5, sendGetCapabilities)


def sendGetCapabilities():
    global gotResponse
    bus.callMethod(
            '/org/freedesktop/Notifications', 'GetCapabilities',
            interface='org.freedesktop.Notifications',
            destination='org.freedesktop.Notifications',
            onReturn=onGetCapabilitiesReturn
            )
    return not gotResponse


def onGetCapabilitiesReturn(response):
    global gotResponse
    gotResponse = True
    logger.info("Got capabilities from notification daemon: %r.", response.body)

    title = "A notification!"
    msg = "Text and stuff."
    logger.info("Sending notification message with title %r: %r.", title, msg)
    bus.callMethod(
            '/org/freedesktop/Notifications', 'Notify',
            'susssasa{ss}i',
            [
                "fttpwm",  # app_name
                0,         # notification_id (spec calls this "replaces_id")
                "",        # app_icon
                title,     # summary
                msg,       # body
                [],        # actions
                {},        # hints
                -1,        # expire_timeout
                ],
            interface='org.freedesktop.Notifications',
            destination='org.freedesktop.Notifications',
            onReturn=onNotifyReturn
            )


def onNotifyReturn(response):
    logger.info("Got response %r from notification daemon, with body %r.", response, response.body)


eventloop.callWhenIdle(connect)
eventloop.run()
