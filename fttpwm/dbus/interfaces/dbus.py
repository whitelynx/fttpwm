# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: D-Bus DBus interface

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import logging

from ..interface import DBusInterface, Method, Signal


logger = logging.getLogger("fttpwm.dbus.interfaces.dbus")


class DBus(DBusInterface('org.freedesktop.DBus')):
    """The message bus accepts connections from one or more applications. Once connected, applications can exchange
    messages with other applications that are also connected to the bus.

    In order to route messages among connections, the message bus keeps a mapping from names to connections. Each
    connection has one unique-for-the-lifetime-of-the-bus name automatically assigned. Applications may request
    additional names for a connection. Additional names are usually "well-known names" such as
    "org.freedesktop.TextEditor". When a name is bound to a connection, that connection is said to own the name.

    The bus itself owns a special name, org.freedesktop.DBus. This name routes messages to the bus, allowing
    applications to make administrative requests. For example, applications can ask the bus to assign a name to a
    connection.

    Each name may have queued owners. When an application requests a name for a connection and the name is already in
    use, the bus will optionally add the connection to a queue waiting for the name. If the current owner of the name
    disconnects or releases the name, the next connection in the queue will become the new owner.

    This feature causes the right thing to happen if you start two text editors for example; the first one may request
    "org.freedesktop.TextEditor", and the second will be queued as a possible owner of that name. When the first exits,
    the second will take over.

    """
    @Method(outSig='s')
    def Hello(self):
        """org.freedesktop.DBus.Hello

        STRING Hello ()

        Reply arguments:
            Argument	Type	Description
            0	STRING	Unique name assigned to the connection

        Before an application is able to send messages to other applications it must send the
        org.freedesktop.DBus.Hello message to the message bus to obtain a unique name. If an application without a
        unique name tries to send a message to another application, or a message to the message bus itself that isn't
        the org.freedesktop.DBus.Hello message, it will be disconnected from the bus.

        There is no corresponding "disconnect" request; if a client wishes to disconnect from the bus, it simply closes
        the socket (or other communication channel).

        """

    @Method(outSig='as')
    def ListNames(self):
        """org.freedesktop.DBus.ListNames

        ARRAY of STRING ListNames ()

        Reply arguments:
            Argument	Type	Description
            0	ARRAY of STRING	Array of strings where each string is a bus name

        Returns a list of all currently-owned names on the bus.

        """

    @Method(outSig='as')
    def ListActivatableNames(self):
        """org.freedesktop.DBus.ListActivatableNames

        ARRAY of STRING ListActivatableNames ()

        Reply arguments:
            Argument	Type	Description
            0	ARRAY of STRING	Array of strings where each string is a bus name

        Returns a list of all names that can be activated on the bus.

        """

    @Method(inSig='s')
    def NameHasOwner(self, name):
        """org.freedesktop.DBus.NameHasOwner

        BOOLEAN NameHasOwner (in STRING name)

        Message arguments:
            Argument	Type	Description
            0	STRING	Name to check

        Reply arguments:
            Argument	Type	Description
            0	BOOLEAN	Return value, true if the name exists

        Checks if the specified name exists (currently has an owner).

        """

    @Signal(sig='sss')
    def NameOwnerChanged(name, old_owner, new_owner):
        """org.freedesktop.DBus.NameOwnerChanged

        NameOwnerChanged (STRING name, STRING old_owner, STRING new_owner)

        Message arguments:
            Argument	Type	Description
            0	STRING	Name with a new owner
            1	STRING	Old owner or empty string if none
            2	STRING	New owner or empty string if none

        This signal indicates that the owner of a name has changed. It's also the signal to use to detect the
        appearance of new names on the bus.

        """

    @Signal(sig='s')
    def NameLost(name):
        """org.freedesktop.DBus.NameLost

        NameLost (STRING name)

        Message arguments:
            Argument	Type	Description
            0	STRING	Name which was lost

        This signal is sent to a specific application when it loses ownership of a name.

        """

    @Signal(sig='s')
    def NameAcquired(name):
        """org.freedesktop.DBus.NameAcquired

        NameAcquired (STRING name)

        Message arguments:
            Argument	Type	Description
            0	STRING	Name which was acquired

        This signal is sent to a specific application when it gains ownership of a name.

        """

    @Method(inSig='su', outSig='u')
    def StartServiceByName(self, name, flags):
        """org.freedesktop.DBus.StartServiceByName

        UINT32 StartServiceByName (in STRING name, in UINT32 flags)

        Message arguments:
            Argument	Type	Description
            0	STRING	Name of the service to start
            1	UINT32	Flags (currently not used)

        Reply arguments:
            Argument	Type	Description
            0	UINT32	Return value

        Tries to launch the executable associated with a name. For more information, see the section called "Message
        Bus Starting Services".

        The return value can be one of the following values:

        Identifier	Value	Description
        DBUS_START_REPLY_SUCCESS	1	The service was successfully started.
        DBUS_START_REPLY_ALREADY_RUNNING	2	A connection already owns the given name.

        """

    @Method(inSig='a{ss}')
    def UpdateActivationEnvironment(self, environment):
        """org.freedesktop.DBus.UpdateActivationEnvironment

        UpdateActivationEnvironment (in ARRAY of DICT<STRING,STRING> environment)

        Message arguments:
            Argument	Type	Description
            0	ARRAY of DICT<STRING,STRING>	Environment to add or update

        Normally, session bus activated services inherit the environment of the bus daemon. This method adds to or
        modifies that environment when activating services.

        Some bus instances, such as the standard system bus, may disable access to this method for some or all callers.

        Note, both the environment variable names and values must be valid UTF-8. There's no way to update the
        activation environment with data that is invalid UTF-8.

        """

    @Method(inSig='s', outSig='s')
    def GetNameOwner(self, name):
        """org.freedesktop.DBus.GetNameOwner

        STRING GetNameOwner (in STRING name)

        Message arguments:
            Argument	Type	Description
            0	STRING	Name to get the owner of

        Reply arguments:
            Argument	Type	Description
            0	STRING	Return value, a unique connection name

        Returns the unique connection name of the primary owner of the name given. If the requested name doesn't have
        an owner, returns a org.freedesktop.DBus.Error.NameHasNoOwner error.

        """

    @Method(inSig='s', outSig='u')
    def GetConnectionUnixUser(self, bus_name):
        """org.freedesktop.DBus.GetConnectionUnixUser

        UINT32 GetConnectionUnixUser (in STRING bus_name)

        Message arguments:
            Argument	Type	Description
            0	STRING	Unique or well-known bus name of the connection to query, such as :12.34 or com.example.tea

        Reply arguments:
            Argument	Type	Description
            0	UINT32	Unix user ID

        Returns the Unix user ID of the process connected to the server. If unable to determine it (for instance,
        because the process is not on the same machine as the bus daemon), an error is returned.

        """

    @Method(inSig='s', outSig='u')
    def GetConnectionUnixProcessID(self, bus_name):
        """org.freedesktop.DBus.GetConnectionUnixProcessID

        UINT32 GetConnectionUnixProcessID (in STRING bus_name)

        Message arguments:
            Argument	Type	Description
            0	STRING	Unique or well-known bus name of the connection to query, such as :12.34 or com.example.tea

        Reply arguments:
            Argument	Type	Description
            0	UINT32	Unix process id

        Returns the Unix process ID of the process connected to the server. If unable to determine it (for instance,
        because the process is not on the same machine as the bus daemon), an error is returned.

        """

    @Method(inSig='s')
    def AddMatch(self, rule):
        """org.freedesktop.DBus.AddMatch

        AddMatch (in STRING rule)

        Message arguments:
            Argument	Type	Description
            0	STRING	Match rule to add to the connection

        Adds a match rule to match messages going through the message bus (see the section called "Match Rules"). If
        the bus does not have enough resources the org.freedesktop.DBus.Error.OOM error is returned.

        """

    @Method(inSig='s')
    def RemoveMatch(self, rule):
        """org.freedesktop.DBus.RemoveMatch

        RemoveMatch (in STRING rule)

        Message arguments:
            Argument	Type	Description
            0	STRING	Match rule to remove from the connection

        Removes the first rule that matches (see the section called "Match Rules"). If the rule is not found the
        org.freedesktop.DBus.Error.MatchRuleNotFound error is returned.

        """

    @Method(outSig='s')
    def GetId(self):
        """org.freedesktop.DBus.GetId

        GetId (out STRING id)

        Reply arguments:
            Argument	Type	Description
            0	STRING	Unique ID identifying the bus daemon

        """
