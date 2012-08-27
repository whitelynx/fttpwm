# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: D-Bus notification example

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import logging

from fttpwm import logconfig


logconfig.configure()

logger = logging.getLogger("fttpwm.examples.notify")


from fttpwm.dbus.bus import SessionBus
from fttpwm.notify.client import Server, Notification

try:
    from fttpwm.eventloop.zmq_loop import ZMQEventLoop

    eventloop = ZMQEventLoop()
    logger.info("Using the ZeroMQ event loop.")

except ImportError:
    logger.warn("Couldn't import ZeroMQ event loop! Falling back to polling event loop.", exc_info=True)

    from fttpwm.eventloop.poll_loop import PollEventLoop

    eventloop = PollEventLoop()


bus = None
server = None

notification = None
notificationCount = 1
maxNotificationCount = 20


def connect():
    global bus, server
    print("\033[1;42;38;5;16mconnect\033[m")
    SessionBus.machineID = '07b6ac7a4c79d9b9628392f30000bea1'
    bus = SessionBus()
    bus.identified.connect(onIdentified)
    server = Server(bus)


def onIdentified():
    global gotResponse
    print("\033[1;43;38;5;16monIdentified\033[m")
    sendGetCapabilities()


def sendGetCapabilities():
    global server
    print("\033[1;46;38;5;16mGetCapabilities\033[m")
    cb = server.GetCapabilities()
    cb.onReturn = onGetCapabilitiesReturn


def onGetCapabilitiesReturn(response):
    global notification
    logger.info("Got capabilities from notification daemon: %r.", response.body)
    notification = Notification('fttpwm', '', '')
    sendNotification()


def sendNotification():
    global notification
    print("\033[1;45;38;5;16mNotify\033[m")

    notification.summary = "A notification!"
    notification.body = "This is message number {}.".format(notificationCount)
    logger.info("Showing notification message with title %r: %r.", notification.summary, notification.body)

    notification.show(onReturn=onNotifyReturn)


def onNotifyReturn(response):
    global notificationCount
    if notificationCount < maxNotificationCount:
        notificationCount += 1

        sendNotification()

    else:
        eventloop.exit()


eventloop.callWhenIdle(connect)
eventloop.run()
