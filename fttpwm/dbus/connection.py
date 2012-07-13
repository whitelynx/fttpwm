# -*- cod-ing: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: D-Bus client connection

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

NOTE: This implementation ONLY supports UNIX domain sockets currently. This will most likely be extended in the future,
but for now it limits what you can connect to.

"""
from cStringIO import StringIO
import errno
import io
import logging
import os
from os.path import exists, expanduser
import re
import socket
import urllib
import warnings

from .. import signals, singletons
from ..utils import loggerFor
from ..eventloop.base import StreamEvents

from .auth import CookieSHA1Auth, AnonymousAuth
#from .proxy import signal, method
from . import message, types
from .errors import NotEnoughData


logger = logging.getLogger('fttpwm.dbus.connection')


class RWBuffer(object):
    READ = object()
    WRITE = object()

    class _BaseInterface(io.IOBase):
        def __init__(self, rwBuf):
            self.rwBuf = rwBuf
            self.position = 0

        def seekable(self):
            return True

        def seek(self, pos, mode=0):
            self.rwBuf.buffer.seek(pos, mode)

            if mode == 0:
                self.position = pos
            elif mode == 1:
                self.position += pos
            else:
                self.position = self.rwBuf.buffer.tell()

            return self.position

        def tell(self):
            return self.position

    class _ReadInterface(_BaseInterface):
        def readable(self):
            return True

        def read(self, n=-1):
            self.rwBuf._ensureMode(RWBuffer.READ, self.position)
            data = self.rwBuf.buffer.read(n)
            self.position += len(data)
            return data

    class _WriteInterface(_BaseInterface):
        def writable(self):
            return True

        def write(self, s):
            if not isinstance(s, bytes):
                warnings.warn("Non-bytes object being written to RWBuffer!", BytesWarning)

            self.rwBuf._ensureMode(RWBuffer.WRITE, self.position)
            self.rwBuf.buffer.write(s)
            self.position += len(s)

    def _ensureMode(self, mode, curPosition):
        if self.currentMode != mode:
            self.currentMode = mode
            self.buffer.seek(curPosition)

    def __init__(self):
        self.buffer = StringIO()
        self.reader = self._ReadInterface(self)
        self.writer = self._WriteInterface(self)
        self.currentMode = self.READ

    def clearReadData(self):
        assert self.reader.position <= self.writer.position

        logger.debug("RWBuffer: Clearing read data.")

        oldBuffer = self.buffer
        oldBuffer.seek(self.reader.position)

        self.writer.position -= self.reader.position
        self.reader.position = 0

        self.buffer = StringIO()
        self.buffer.write(oldBuffer.read())
        self.buffer.seek(0)
        self.currentMode = self.READ


class Callbacks(object):
    def __init__(self, onReturn=None, onError=None):
        self.onReturn = onReturn or (lambda response: None)
        self.onError = onError or (lambda response: None)


class Connection(object):
    authenticators = [
            CookieSHA1Auth,
            AnonymousAuth
            ]

    def __init__(self, address=None):
        self.logger = loggerFor(self)

        self.serverUUID = None
        self.reportedAuthMechanisms = None
        self.uniqueID = None
        self.callbacks = dict()
        self.isAuthenticated = False

        self.incoming = RWBuffer()
        self.outgoing = RWBuffer()

        self.connected = signals.Signal()
        self.authenticated = signals.Signal()
        self.disconnected = signals.Signal()

        if address is not None:
            self.connect(address)

    @property
    def serverGUID(self):
        """Alternate name for serverUUID, for backwards compatability.

        """
        return self.serverUUID

    @property
    def machineID(self):
        #FIXME: I have absolutely no idea how to get this! The spec doesn't seem to say.
        return '07b6ac7a4c79d9b9628392f30000bea1'

    def parseAddressOptions(self, optionString):
        options = dict()

        for kvp in optionString.split(','):
            key, value = kvp.split('=')
            options[key] = urllib.unquote(value)

        return options

    def connect(self, addresses):
        addresses = addresses.split(';')
        self.logger.debug("Attempting to connect to addresses:\n  %s", '\n  '.join(addresses))
        self.addressIter = iter(addresses)
        self.nextConnection()

    def nextConnection(self):
        try:
            self.address = self.addressIter.next()
        except StopIteration:
            self.logger.error("Couldn't connect to any D-Bus servers! Giving up.")
            raise RuntimeError("Couldn't connect to any D-Bus servers! Giving up.")

        self.authenticatorIter = iter(self.authenticators)

        transport, options = self.address.split(':', 1)

        connectMethod = getattr(self, 'connect_' + transport, None)
        if connectMethod is not None:
            options = self.parseAddressOptions(options)

            self.logger.debug("Connecting to %r...", self.address)
            if not connectMethod(**options):
                self.logger.warn("Connection to %r failed!", transport)
                self.nextConnection()

        else:
            self.logger.warn("Unsupported D-Bus connection transport: %r", transport)

    def connect_unix(self, **kwargs):
        try:
            socketAddress = kwargs['path']
        except KeyError:
            try:
                # The D-Bus spec doesn't mention it, but abstract namespace UNIX domain sockets on Linux start
                # with a null byte.
                socketAddress = '\0' + kwargs['abstract']
            except KeyError:
                logger.warn("Got a 'unix' address without either 'path' or 'abstract' specified!")
                return False

        try:
            self.socket = socket.socket(socket.AF_UNIX)
            self.socket.connect(socketAddress)

            #FIXME: Right now, this will probably cause issues if connect_unix ever gets called multiple times!
            singletons.eventloop.register(self.socket, self.handleIO,
                    events=(StreamEvents.INCOMING, StreamEvents.OUTGOING))

            self.connected()

            # Start authentication process.
            self.send('\0')
            self.authenticate()

            return True

        except:
            self.logger.exception("Exception encountered while attempting to connect to D-Bus!")
            return False

    def authenticate(self):
        try:
            self.authenticator = self.authenticatorIter.next()
        except StopIteration:
            self.logger.warn("All supported authentication methods failed! Trying next connection...")
            self.nextConnection()

        if self.reportedAuthMechanisms is not None and self.authenticator.name not in self.reportedAuthMechanisms:
            # The server doesn't support this authentication method; skip it.
            self.authenticate()

        try:
            self.logger.debug("Attempting authentication with mechanism %s...", self.authenticator.name)
            self.authenticator = self.authenticator(self)

            self.authenticator.authenticate()

        except:
            self.logger.exception(
                    "Exception encountered while attempting authentication with mechanism %s!",
                    self.authenticator.name
                    )

    def authSucceeded(self):
        self.logger.info("Authentication succeeded.")
        self.isAuthenticated = True
        self.authenticated()

    def authFailed(self):
        self.logger.info("Authentication failed; trying next method.")
        self.authenticate()

    def callMethod(self, objectPath, member, inSignature='', args=[], interface=None, destination=None, onReturn=None,
            onError=None):
        msg = message.Message(inSignature)

        h = msg.header
        h.messageType = message.Types.METHOD_CALL

        h.headerFields[message.HeaderFields.PATH] = types.Variant(types.ObjectPath, objectPath)
        h.headerFields[message.HeaderFields.MEMBER] = types.Variant(types.String, member)

        if interface is not None:
            h.headerFields[message.HeaderFields.INTERFACE] = types.Variant(types.String, interface)
        if destination is not None:
            h.headerFields[message.HeaderFields.DESTINATION] = types.Variant(types.String, destination)

        msg.body = args

        print("\033[1;48;5;236;38;5;16mout <<< {}\033[m".format(msg))
        self.send(msg.render())
        self.callbacks[msg.header.serial] = Callbacks(onReturn, onError)

    def send(self, data):
        self.outgoing.writer.write(data)

    def handleIO(self, stream, evt):
        if evt == StreamEvents.INCOMING:
            self.handleRead()
        elif evt == StreamEvents.OUTGOING:
            self.handleWrite()
        else:
            self.logger.error("Unrecognized stream event: %r", evt)

    def handleWrite(self):
        startPos = self.outgoing.reader.tell()
        data = self.outgoing.reader.read()

        if len(data) > 0:
            print("\033[1;44;38;5;16mhandleWrite\033[m")
            sent = self.socket.send(data)
            self.outgoing.reader.seek(startPos + sent)
            self.logger.debug("Wrote %s bytes from outgoing buffer to socket.", sent)

            if sent == len(data):
                # Clear sent data so the next message is aligned correctly.
                self.outgoing.clearReadData()

    def handleRead(self):
        print("\033[1;41;38;5;16mhandleRead\033[m")
        """Read all incoming data from the D-Bus server, and process all resulting messages.

        """
        try:
            data = self.socket.recv(8192)
        except socket.error as ex:
            logger.exception("Encountered socket error %s (%s) while receiving: %s", ex.errno, ex.strerror, ex.message)
            raise

        #curPos = self.incoming.reader.position
        #self.incoming.reader.seek(0, 2)
        #endPos = self.incoming.reader.position
        #self.incoming.reader.seek(curPos)
        #self.logger.debug("%s bytes unread in incoming buffer.", endPos - self.incoming.reader.position)

        writePos = self.incoming.writer.position
        self.incoming.writer.write(data)
        self.logger.debug("Wrote %s bytes from socket to incoming buffer at position %s.", len(data), writePos)
        self.logger.trace("Incoming data: %r", data)

        #curPos = self.incoming.reader.position
        #self.incoming.reader.seek(0, 2)
        #endPos = self.incoming.reader.position
        #self.incoming.reader.seek(curPos)
        #self.logger.debug("%s bytes unread in incoming buffer.", endPos - self.incoming.reader.position)

        while True:
            if self.incoming.reader.position != 0:
                # Clear read data so the next message is aligned correctly.
                #pos = self.incoming.reader.position
                #self.incoming.reader.seek(0)
                #self.logger.trace("Discarding %s bytes of read data: %r", pos, self.incoming.reader.read(pos))
                #self.incoming.reader.seek(pos)

                self.incoming.clearReadData()

            startPos = self.incoming.reader.position
            try:
                if self.isAuthenticated:
                    self.handleMessageRead()
                else:
                    self.handleAuthRead()

            except NotEnoughData:
                # Give up parsing for now; we'll get more next time we get a receive callback.
                self.incoming.reader.position = startPos
                return

    def handleAuthRead(self):
        try:
            self.authenticator.handleRead(self.incoming.reader)

        except NotEnoughData:
            raise

        except Exception:
            logger.exception("Got unrecognized exception while parsing incoming authentication message!")
            raise

    def handleMessageRead(self):
        try:
            response = message.Message.parseFile(self.incoming.reader)
            print("\033[1;100;38;5;16min >>> {!r}\033[m".format(response))

        except NotEnoughData:
            raise

        except Exception:
            logger.exception("Got unrecognized exception while parsing incoming message! Skipping.")
            raise

        else:
            try:
                inReplyTo = response.header.headerFields[message.HeaderFields.REPLY_SERIAL]

            except KeyError:
                self.handleNonResponse(response)

            else:
                self.handleResponse(response, inReplyTo)

    def handleResponse(self, response, inReplyTo):
        # A response message! Look up the method call that goes with it.
        try:
            callbacks = self.callbacks.pop(inReplyTo)
        except KeyError:
            logger.error(
                    "Got a response message, but we don't have a record of the message it's replying to, %r!",
                    inReplyTo
                    )
            return

        if response.header.messageType == message.Types.ERROR:
            callbacks.onError(response)

        elif response.header.messageType == message.Types.METHOD_RETURN:
            callbacks.onReturn(response)

        else:
            logger.error(
                    "Got a response to message %r, but it wasn't a METHOD_RETURN or ERROR! Response = %r",
                    inReplyTo,
                    response
                    )

    def handleNonResponse(self, response):
        # Not a response message; check for incoming signals and method calls.
        if response.header.messageType == message.Types.SIGNAL:
            warnings.warn("Not yet implemented: Got SIGNAL message: {}".format(response), FutureWarning)
        elif response.header.messageType == message.Types.METHOD_CALL:
            warnings.warn("Not yet implemented: Got METHOD_CALL message: {}".format(response), FutureWarning)

    def close(self):
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()


class Bus(Connection):
    def __init__(self, address=None):
        super(Bus, self).__init__(address)

        self.identified = signals.Signal()

        self.authenticated.connect(self.sayHello)

    def sayHello(self):
        def onReturn(response):
            self.uniqueID, = response.body

            logger.info("Got unique name %r from message bus.", self.uniqueID)

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

    @property
    def defaultAddress(self):
        return os.environ.get('DBUS_SYSTEM_BUS_ADDRESS', 'unix:path=/var/run/dbus/system_bus_socket')
