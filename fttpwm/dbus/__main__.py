# -*- cod-ing: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: D-Bus client test

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import logging

from . import connection, message, types


logging.basicConfig(level=logging.NOTSET)

bus = connection.SessionBus()
bus.connect()

m = message.Message()
m.header.messageType = message.Types.METHOD_CALL
m.header.headerFields[message.HeaderFields.PATH] = types.VARIANT()(types.STRING(), '/org/freedesktop/DBus')
m.header.headerFields[message.HeaderFields.INTERFACE] = types.VARIANT()(types.STRING(), 'org.freedesktop.DBus')
m.header.headerFields[message.HeaderFields.MEMBER] = types.VARIANT()(types.STRING(), 'Hello')
m.header.headerFields[message.HeaderFields.DESTINATION] = types.VARIANT()(types.STRING(), 'org.freedesktop.DBus')

bus.send(m.render())

print(message.Message.parseMessage(bus.recv()))
