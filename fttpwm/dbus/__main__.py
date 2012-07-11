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

bus = connection.SessionBus()
bus.connect()


def onReturn(response):
    logger.info("Got response %r from notification daemon, with body %r.", response, response.body)


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
        onReturn=onReturn
        )
