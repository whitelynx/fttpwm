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

    @Method(inSig='su', outSig='u')
    def RequestName(self):
        """org.freedesktop.DBus.RequestName

        UINT32 RequestName (in STRING name, in UINT32 flags)

        Message arguments:
            Argument  Type    Description
            0         STRING  Name to request
            1         UINT32  Flags

        Reply arguments:
            Argument  Type    Description
            0         UINT32  Return value

        This method call should be sent to org.freedesktop.DBus and asks the message bus to assign the given name to
        the method caller. Each name maintains a queue of possible owners, where the head of the queue is the primary
        or current owner of the name. Each potential owner in the queue maintains the DBUS_NAME_FLAG_ALLOW_REPLACEMENT
        and DBUS_NAME_FLAG_DO_NOT_QUEUE settings from its latest RequestName call. When RequestName is invoked the
        following occurs:

         - If the method caller is currently the primary owner of the name, the DBUS_NAME_FLAG_ALLOW_REPLACEMENT and
            DBUS_NAME_FLAG_DO_NOT_QUEUE values are updated with the values from the new RequestName call, and nothing
            further happens.

         - If the current primary owner (head of the queue) has DBUS_NAME_FLAG_ALLOW_REPLACEMENT set, and the
            RequestName invocation has the DBUS_NAME_FLAG_REPLACE_EXISTING flag, then the caller of RequestName
            replaces the current primary owner at the head of the queue and the current primary owner moves to the
            second position in the queue. If the caller of RequestName was in the queue previously its flags are
            updated with the values from the new RequestName in addition to moving it to the head of the queue.

         - If replacement is not possible, and the method caller is currently in the queue but not the primary owner,
            its flags are updated with the values from the new RequestName call.

         - If replacement is not possible, and the method caller is currently not in the queue, the method caller is
            appended to the queue.

         - If any connection in the queue has DBUS_NAME_FLAG_DO_NOT_QUEUE set and is not the primary owner, it is
            removed from the queue. This can apply to the previous primary owner (if it was replaced) or the method
            caller (if it updated the DBUS_NAME_FLAG_DO_NOT_QUEUE flag while still stuck in the queue, or if it was
            just added to the queue with that flag set).

        Note that DBUS_NAME_FLAG_REPLACE_EXISTING results in "jumping the queue," even if another application already
        in the queue had specified DBUS_NAME_FLAG_REPLACE_EXISTING. This comes up if a primary owner that does not
        allow replacement goes away, and the next primary owner does allow replacement. In this case, queued items that
        specified DBUS_NAME_FLAG_REPLACE_EXISTING do not automatically replace the new primary owner. In other words,
        DBUS_NAME_FLAG_REPLACE_EXISTING is not saved, it is only used at the time RequestName is called. This is
        deliberate to avoid an infinite loop anytime two applications are both DBUS_NAME_FLAG_ALLOW_REPLACEMENT and
        DBUS_NAME_FLAG_REPLACE_EXISTING.

        The flags argument contains any of the following values logically ORed together:

            Conventional Name                 Value  Description
            DBUS_NAME_FLAG_ALLOW_REPLACEMENT  0x1    If an application A specifies this flag and succeeds in becoming
                                                     the owner of the name, and another application B later calls
                                                     RequestName with the DBUS_NAME_FLAG_REPLACE_EXISTING flag, then
                                                     application A will lose ownership and receive a
                                                     org.freedesktop.DBus.NameLost signal, and application B will
                                                     become the new owner. If DBUS_NAME_FLAG_ALLOW_REPLACEMENT is not
                                                     specified by application A, or DBUS_NAME_FLAG_REPLACE_EXISTING is
                                                     not specified by application B, then application B will not
                                                     replace application A as the owner.
            DBUS_NAME_FLAG_REPLACE_EXISTING   0x2    Try to replace the current owner if there is one. If this flag is
                                                     not set the application will only become the owner of the name if
                                                     there is no current owner. If this flag is set, the application
                                                     will replace the current owner if the current owner specified
                                                     DBUS_NAME_FLAG_ALLOW_REPLACEMENT.
            DBUS_NAME_FLAG_DO_NOT_QUEUE       0x4    Without this flag, if an application requests a name that is
                                                     already owned, the application will be placed in a queue to own
                                                     the name when the current owner gives it up. If this flag is
                                                     given, the application will not be placed in the queue, the
                                                     request for the name will simply fail. This flag also affects
                                                     behavior when an application is replaced as name owner; by default
                                                     the application moves back into the waiting queue, unless this
                                                     flag was provided when the application became the name owner.

        The return code can be one of the following values:

            Conventional Name                      Value  Description
            DBUS_REQUEST_NAME_REPLY_PRIMARY_OWNER  1      The caller is now the primary owner of the name, replacing
                                                          any previous owner. Either the name had no owner before, or
                                                          the caller specified DBUS_NAME_FLAG_REPLACE_EXISTING and the
                                                          current owner specified DBUS_NAME_FLAG_ALLOW_REPLACEMENT.
            DBUS_REQUEST_NAME_REPLY_IN_QUEUE       2      The name already had an owner, DBUS_NAME_FLAG_DO_NOT_QUEUE
                                                          was not specified, and either the current owner did not
                                                          specify DBUS_NAME_FLAG_ALLOW_REPLACEMENT or the requesting
                                                          application did not specify DBUS_NAME_FLAG_REPLACE_EXISTING.
            DBUS_REQUEST_NAME_REPLY_EXISTS         3      The name already has an owner, DBUS_NAME_FLAG_DO_NOT_QUEUE
                                                          was specified, and either DBUS_NAME_FLAG_ALLOW_REPLACEMENT
                                                          was not specified by the current owner, or
                                                          DBUS_NAME_FLAG_REPLACE_EXISTING was not specified by the
                                                          requesting application.
            DBUS_REQUEST_NAME_REPLY_ALREADY_OWNER  4      The application trying to request ownership of a name is
                                                          already the owner of it.

        """

    @Method(inSig='s', outSig='u')
    def ReleaseName(self):
        """org.freedesktop.DBus.ReleaseName

        UINT32 ReleaseName (in STRING name)


        Message arguments:
            Argument  Type    Description
            0         STRING  Name to release

        Reply arguments:
            Argument  Type    Description
            0         UINT32  Return value

        This method call should be sent to org.freedesktop.DBus and asks the message bus to release the method caller's
        claim to the given name. If the caller is the primary owner, a new primary owner will be selected from the
        queue if any other owners are waiting. If the caller is waiting in the queue for the name, the caller will
        removed from the queue and will not be made an owner of the name if it later becomes available. If there are no
        other owners in the queue for the name, it will be removed from the bus entirely. The return code can be one of
        the following values:

            Conventional Name                     Value  Description
            DBUS_RELEASE_NAME_REPLY_RELEASED      1      The caller has released his claim on the given name. Either
                                                         the caller was the primary owner of the name, and the name is
                                                         now unused or taken by somebody waiting in the queue for the
                                                         name, or the caller was waiting in the queue for the name and
                                                         has now been removed from the queue.
            DBUS_RELEASE_NAME_REPLY_NON_EXISTENT  2      The given name does not exist on this bus.
            DBUS_RELEASE_NAME_REPLY_NOT_OWNER     3      The caller was not the primary owner of this name, and was
                                                         also not waiting in the queue to own this name.
        """

    @Method(inSig='s', outSig='as')
    def ListQueuedOwners(self):
        """org.freedesktop.DBus.ListQueuedOwners

        ARRAY of STRING ListQueuedOwners (in STRING name)

        Message arguments:
        Argument  Type    Description
        0         STRING  The well-known bus name to query, such as com.example.cappuccino

        Reply arguments:
        Argument  Type             Description
        0         ARRAY of STRING  The unique bus names of connections currently queued for the name

        This method call should be sent to org.freedesktop.DBus and lists the connections currently queued for a bus
        name.

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
