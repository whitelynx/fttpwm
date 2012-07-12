# -*- cod-ing: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: D-Bus client test

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import logging

from . import connection


logging.basicConfig(level=logging.NOTSET)

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


def connect():
    global bus
    print("\033[1;90;42mconnect\033[m")
    bus = connection.SessionBus()
    bus.identified.connect(onIdentified)


def onIdentified():
    print("\033[1;90;43monIdentified\033[m")
    eventloop.callEvery(0.5, sendGetCapabilities)


def sendGetCapabilities():
    bus.callMethod(
            '/org/freedesktop/Notifications', 'GetCapabilities',
            interface='org.freedesktop.Notifications',
            destination='org.freedesktop.Notifications',
            onReturn=onGetCapabilitiesReturn
            )
    return True


def onGetCapabilitiesReturn(response):
    logger.info("Got capabilities from notification daemon: %r.", response.body)

    bus.callMethod(
            '/org/freedesktop/Notifications', 'Notify',
            'susssasa{ss}i',
            [
                "fttpwm",           # app_name
                0,                  # notification_id (spec calls this "replaces_id")
                "",                 # app_icon
                "A notification!",  # summary
                "Text and stuff.",  # body
                [],                 # actions
                {},                 # hints
                -1,                 # expire_timeout
                ],
            interface='org.freedesktop.Notifications',
            destination='org.freedesktop.Notifications',
            onReturn=onNotifyReturn
            )


def onNotifyReturn(response):
    logger.info("Got response %r from notification daemon, with body %r.", response, response.body)


eventloop.callWhenIdle(connect)
eventloop.run()
