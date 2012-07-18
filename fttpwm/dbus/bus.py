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
#from .proxy import signal, method


class Bus(Connection):
    def __init__(self, address=None):
        super(Bus, self).__init__(address)

        self.logger = loggerFor(self)
        self.identified = signals.Signal()

        self.authenticated.connect(self.sayHello)

    def sayHello(self):
        def onReturn(response):
            self.uniqueID, = response.body

            self.logger.info("Got unique name %r from message bus.", self.uniqueID)

            self.identified()

        self.callMethod(
                '/org/freedesktop/DBus', 'Hello',
                interface='org.freedesktop.DBus',
                destination='org.freedesktop.DBus',
                onReturn=onReturn
                )

    """
    ## Proxies for org.freedesktop.DBus methods ##
    @method
    def hello(self):
        '''org.freedesktop.DBus.Hello

        STRING Hello ()

        Reply arguments:

        Argument	Type	Description
        0	STRING	Unique name assigned to the connection
        Before an application is able to send messages to other applications it must send the org.freedesktop.DBus.Hello message to the message bus to obtain a unique name. If an application without a unique name tries to send a message to another application, or a message to the message bus itself that isn't the org.freedesktop.DBus.Hello message, it will be disconnected from the bus.

        There is no corresponding "disconnect" request; if a client wishes to disconnect from the bus, it simply closes the socket (or other communication channel).

        '''

    @method
    def listNames(self):
        '''org.freedesktop.DBus.ListNames

        ARRAY of STRING ListNames ()

        Reply arguments:

        Argument	Type	Description
        0	ARRAY of STRING	Array of strings where each string is a bus name
        Returns a list of all currently-owned names on the bus.

        '''

    @method
    def listActivatableNames(self):
        '''org.freedesktop.DBus.ListActivatableNames

        ARRAY of STRING ListActivatableNames ()

        Reply arguments:

        Argument	Type	Description
        0	ARRAY of STRING	Array of strings where each string is a bus name
        Returns a list of all names that can be activated on the bus.

        '''

    @method
    def nameHasOwner(self, name):
        '''org.freedesktop.DBus.NameHasOwner

        BOOLEAN NameHasOwner (in STRING name)

        Message arguments:

        Argument	Type	Description
        0	STRING	Name to check
        Reply arguments:

        Argument	Type	Description
        0	BOOLEAN	Return value, true if the name exists
        Checks if the specified name exists (currently has an owner).

        '''

    @signal
    def nameOwnerChanged(name, old_owner, new_owner):
        '''org.freedesktop.DBus.NameOwnerChanged

        NameOwnerChanged (STRING name, STRING old_owner, STRING new_owner)

        Message arguments:

        Argument	Type	Description
        0	STRING	Name with a new owner
        1	STRING	Old owner or empty string if none
        2	STRING	New owner or empty string if none
        This signal indicates that the owner of a name has changed. It's also the signal to use to detect the appearance of new names on the bus.

        '''

    @signal
    def nameLost(name):
        '''org.freedesktop.DBus.NameLost

        NameLost (STRING name)

        Message arguments:

        Argument	Type	Description
        0	STRING	Name which was lost
        This signal is sent to a specific application when it loses ownership of a name.

        '''

    @signal
    def nameAcquired(name):
        '''org.freedesktop.DBus.NameAcquired

        NameAcquired (STRING name)

        Message arguments:

        Argument	Type	Description
        0	STRING	Name which was acquired
        This signal is sent to a specific application when it gains ownership of a name.

        '''

    @method
    def startServiceByName(self, name, flags):
        '''org.freedesktop.DBus.StartServiceByName

        UINT32 StartServiceByName (in STRING name, in UINT32 flags)

        Message arguments:

        Argument	Type	Description
        0	STRING	Name of the service to start
        1	UINT32	Flags (currently not used)
        Reply arguments:

        Argument	Type	Description
        0	UINT32	Return value
        Tries to launch the executable associated with a name. For more information, see the section called "Message Bus Starting Services".

        The return value can be one of the following values:

        Identifier	Value	Description
        DBUS_START_REPLY_SUCCESS	1	The service was successfully started.
        DBUS_START_REPLY_ALREADY_RUNNING	2	A connection already owns the given name.

        '''

    @method
    def updateActivationEnvironment(self, environment):
        '''org.freedesktop.DBus.UpdateActivationEnvironment

        UpdateActivationEnvironment (in ARRAY of DICT<STRING,STRING> environment)

        Message arguments:

        Argument	Type	Description
        0	ARRAY of DICT<STRING,STRING>	Environment to add or update
        Normally, session bus activated services inherit the environment of the bus daemon. This method adds to or modifies that environment when activating services.

        Some bus instances, such as the standard system bus, may disable access to this method for some or all callers.

        Note, both the environment variable names and values must be valid UTF-8. There's no way to update the activation environment with data that is invalid UTF-8.

        '''

    @method
    def getNameOwner(self, name):
        '''org.freedesktop.DBus.GetNameOwner

        STRING GetNameOwner (in STRING name)

        Message arguments:

        Argument	Type	Description
        0	STRING	Name to get the owner of
        Reply arguments:

        Argument	Type	Description
        0	STRING	Return value, a unique connection name
        Returns the unique connection name of the primary owner of the name given. If the requested name doesn't have an owner, returns a org.freedesktop.DBus.Error.NameHasNoOwner error.

        '''

    @method
    def getConnectionUnixUser(self, bus_name):
        '''org.freedesktop.DBus.GetConnectionUnixUser

        UINT32 GetConnectionUnixUser (in STRING bus_name)

        Message arguments:

        Argument	Type	Description
        0	STRING	Unique or well-known bus name of the connection to query, such as :12.34 or com.example.tea
        Reply arguments:

        Argument	Type	Description
        0	UINT32	Unix user ID
        Returns the Unix user ID of the process connected to the server. If unable to determine it (for instance, because the process is not on the same machine as the bus daemon), an error is returned.

        '''

    @method
    def getConnectionUnixProcessID(self, bus_name):
        '''org.freedesktop.DBus.GetConnectionUnixProcessID

        UINT32 GetConnectionUnixProcessID (in STRING bus_name)

        Message arguments:

        Argument	Type	Description
        0	STRING	Unique or well-known bus name of the connection to query, such as :12.34 or com.example.tea
        Reply arguments:

        Argument	Type	Description
        0	UINT32	Unix process id
        Returns the Unix process ID of the process connected to the server. If unable to determine it (for instance, because the process is not on the same machine as the bus daemon), an error is returned.

        '''

    @method
    def addMatch(self, rule):
        '''org.freedesktop.DBus.AddMatch

        AddMatch (in STRING rule)

        Message arguments:

        Argument	Type	Description
        0	STRING	Match rule to add to the connection
        Adds a match rule to match messages going through the message bus (see the section called "Match Rules"). If the bus does not have enough resources the org.freedesktop.DBus.Error.OOM error is returned.

        '''

    @method
    def removeMatch(self, rule):
        '''org.freedesktop.DBus.RemoveMatch

        RemoveMatch (in STRING rule)

        Message arguments:

        Argument	Type	Description
        0	STRING	Match rule to remove from the connection
        Removes the first rule that matches (see the section called "Match Rules"). If the rule is not found the org.freedesktop.DBus.Error.MatchRuleNotFound error is returned.

        '''

    @method
    def getId(self, id):
        '''org.freedesktop.DBus.GetId

        GetId (out STRING id)

        Reply arguments:
        0	STRING	Unique ID identifying the bus daemon

        '''
    """


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
