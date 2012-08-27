# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: D-Bus bus connection objects

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import os
from os.path import exists, expanduser
import re

from .. import signals, singletons
from ..utils import loggerFor

from .connection import Connection
from .interfaces.dbus import DBus as DBusInterface
from .interfaces.introspectable import Introspectable as IntrospectableInterface
from .remote import RemoteObject


class Bus(RemoteObject):
    ## DBus interfaces
    dbus = DBusInterface
    introspectable = IntrospectableInterface

    ## DBus object information
    busObjectPath = '/org/freedesktop/DBus'

    def __init__(self, address=None):
        self.connection = Connection(address)
        self.serverUUID = None

        super(Bus, self).__init__(self.busObjectPath, destination='org.freedesktop.DBus', bus=self)

        self.logger = loggerFor(self)
        self.identified = signals.Signal()

        self.authenticated.connect(self.onAuthenticated)

    def __getattr__(self, name):
        return getattr(self.connection, name)

    @property
    def machineID(self):
        return Connection.machineID()

    def onAuthenticated(self):
        cb = self.Hello()
        cb.onReturn = self.onHelloReturn

    def onHelloReturn(self, response):
        self.uniqueID, = response.body

        self.logger.info("Got unique name %r from message bus.", self.uniqueID)
        self.identified()


class SessionBus(Bus):
    displayNameRE = re.compile(r'^(?:(?:localhost(?:\.localdomain)?)?:)?(.*?)(?:\.\d)?$')

    def __init__(self):
        super(SessionBus, self).__init__(address=self.defaultAddress)
        singletons.dbusSessionBus = self

    @property
    def defaultAddress(self):
        #FIXME: Implement getting the session bus address from the _DBUS_SESSION_BUS_ADDRESS property of the window
        # which owns the _DBUS_SESSION_BUS_SELECTION_<username>_<machine ID> X selection.

        # Alternative method, using a file in ~/.dbus/session-bus/ with the name:
        # - the machine's ID
        # - the literal character '-' (dash)
        # - the X display without the screen number, with the following prefixes removed, if present: ":",
        #    "localhost:", "localhost.localdomain:". That is, a display of "localhost:10.0" produces just the number
        #    "10"
        #TODO: There doesn't seem to be any way to get the name of the display we're connected to from xpyb!
        displayName = self.displayNameRE.match(os.environ['DISPLAY']).group(1)
        filename = expanduser('~/.dbus/session-bus/{}-{}'.format(self.machineID, displayName))

        if exists(filename):
            connectionInfo = dict()

            with open(filename, 'r') as file:
                for line in file:
                    if not line.startswith('#') and '=' in line:
                        key, val = line.split('=', 1)
                        connectionInfo[key] = val

            return connectionInfo['DBUS_SESSION_BUS_ADDRESS']

        #FIXME: Implement autostart! From the spec:
        #    Failure to open this file MUST be interpreted as absence of a running server. Therefore, the
        #    implementation MUST proceed to attempting to launch a new bus server if the file cannot be opened.
        #
        #    However, success in opening this file MUST NOT lead to the conclusion that the server is running. Thus, a
        #    failure to connect to the bus address obtained by the alternative method MUST NOT be considered a fatal
        #    error. If the connection cannot be established, the implementation MUST proceed to check the X selection
        #    settings or to start the server on its own.

        return os.environ['DBUS_SESSION_BUS_ADDRESS']


class SystemBus(Bus):
    def __init__(self):
        super(SystemBus, self).__init__(address=self.defaultAddress)
        singletons.dbusSystemBus = self

    @property
    def defaultAddress(self):
        return os.environ.get('DBUS_SYSTEM_BUS_ADDRESS', 'unix:path=/var/run/dbus/system_bus_socket')
