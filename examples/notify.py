# -*- cod-ing: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: D-Bus notification example

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import logging

from fttpwm import logconfig


logconfig.configure()

logger = logging.getLogger("fttpwm.dbus.__main__")


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

notificationID = 0  # Initially, don't specify an ID
notificationCount = 1
maxNotificationCount = 20


def connect():
    global bus
    print("\033[1;42;38;5;16mconnect\033[m")
    bus = SessionBus()
    bus.identified.connect(onIdentified)


def onIdentified():
    global gotResponse
    print("\033[1;43;38;5;16monIdentified\033[m")
    sendGetCapabilities()


def sendGetCapabilities():
    print("\033[1;46;38;5;16mGetCapabilities\033[m")
    bus.callMethod(
            '/org/freedesktop/Notifications', 'GetCapabilities',
            interface='org.freedesktop.Notifications',
            destination='org.freedesktop.Notifications',
            onReturn=onGetCapabilitiesReturn
            )


def onGetCapabilitiesReturn(response):
    logger.info("Got capabilities from notification daemon: %r.", response.body)
    sendNotification()


def sendNotification():
    print("\033[1;45;38;5;16mNotify\033[m")
    title = "A notification!"
    msg = "This is message number {}.".format(notificationCount)
    logger.info("Sending notification message with title %r: %r.", title, msg)
    bus.callMethod(
            '/org/freedesktop/Notifications', 'Notify',
            'susssasa{ss}i',
            [
                "fttpwm",        # app_name
                notificationID,  # notification_id (spec calls this "replaces_id")
                "",              # app_icon
                title,           # summary
                msg,             # body
                [],              # actions
                {},              # hints
                -1,              # expire_timeout
                ],
            interface='org.freedesktop.Notifications',
            destination='org.freedesktop.Notifications',
            onReturn=onNotifyReturn
            )


def onNotifyReturn(response):
    global notificationID, notificationCount
    if notificationID == 0:
        notificationID = response.body[0]
        logger.info("Got notification ID %r from notification daemon.", notificationID)

    if notificationCount < maxNotificationCount:
        notificationCount += 1

        sendNotification()

    else:
        eventloop.exit()


eventloop.callWhenIdle(connect)
eventloop.run()
