# -*- cod-ing: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: D-Bus client connection

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

NOTE: This implementation ONLY supports UNIX domain sockets currently. This will most likely be extended in the future,
but for now it limits what you can connect to.

"""
from cStringIO import StringIO
import collections
import io
import socket
import urllib
import warnings

from .. import signals, singletons
from ..utils import loggerFor
from ..eventloop.base import StreamEvents

from .auth import CookieSHA1Auth, AnonymousAuth
#from .proxy import signal, method
from .proto import message, types
from .proto.errors import NotEnoughData


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
        self.logger = loggerFor(self)
        self.buffer = StringIO()
        self.reader = self._ReadInterface(self)
        self.writer = self._WriteInterface(self)
        self.currentMode = self.READ

    def clearReadData(self):
        assert self.reader.position <= self.writer.position

        self.logger.debug("RWBuffer: Clearing read data.")

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
        self.signalHandlers = collections.defaultdict(list)

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
                self.logger.warn("Got a 'unix' address without either 'path' or 'abstract' specified!")
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

        h.headerFields[message.HeaderFields.PATH] = types.Variant(objectPath, types.ObjectPath)
        h.headerFields[message.HeaderFields.MEMBER] = types.Variant(member, types.String)

        if interface is not None:
            h.headerFields[message.HeaderFields.INTERFACE] = types.Variant(interface, types.String)
        if destination is not None:
            h.headerFields[message.HeaderFields.DESTINATION] = types.Variant(destination, types.String)

        msg.body = args

        print("\033[1;48;5;236;38;5;16mout <<< {}\033[m".format(msg))
        self.send(msg.render())
        self.callbacks[msg.header.serial] = Callbacks(onReturn, onError)

    def listenForSignal(self, interface, handler, **kwargs):
        if len(kwargs) > 0:
            raise NotImplemented

        self.signalHandlers[interface].append(handler)

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
        """Read all incoming data from the D-Bus server, and process all resulting messages.

        """
        try:
            data = self.socket.recv(8192)
        except socket.error as ex:
            self.logger.exception("Encountered socket error %s (%s) while receiving: %s",
                    ex.errno, ex.strerror, ex.message)
            raise

        if len(data) == 0:
            #raise IOError("Remote host disconnected!")
            return

        print("\033[1;41;38;5;16mhandleRead\033[m")
        writePos = self.incoming.writer.position
        self.incoming.writer.write(data)
        self.logger.debug("Wrote %s bytes from socket to incoming buffer at position %s.", len(data), writePos)
        self.logger.trace("Incoming data: %r", data)

        while True:
            if self.incoming.reader.position != 0:
                # Clear read data so the next message is aligned correctly.

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
            self.logger.exception("Got unrecognized exception while parsing incoming authentication message!")
            raise

    def handleMessageRead(self):
        try:
            response = message.Message.parseFile(self.incoming.reader)
            print("\033[1;100;38;5;16min >>> {!r}\033[m".format(response))

        except NotEnoughData:
            raise

        except Exception:
            self.logger.exception("Got unrecognized exception while parsing incoming message! Skipping.")
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
            self.logger.error(
                    "Got a response message, but we don't have a record of the message it's replying to, %r!",
                    inReplyTo
                    )
            return

        if response.header.messageType == message.Types.ERROR:
            callbacks.onError(response)

        elif response.header.messageType == message.Types.METHOD_RETURN:
            callbacks.onReturn(response)

        else:
            self.logger.error(
                    "Got a response to message %r, but it wasn't a METHOD_RETURN or ERROR! Response = %r",
                    inReplyTo,
                    response
                    )

    def handleNonResponse(self, incoming):
        # Not a response message; check for incoming signals and method calls.
        if incoming.header.messageType == message.Types.SIGNAL:
            self.handleSignal(incoming)
        elif incoming.header.messageType == message.Types.METHOD_CALL:
            warnings.warn("Not yet implemented: Got METHOD_CALL message: {}".format(incoming), FutureWarning)

    def handleSignal(self, incoming):
        interfaceName = incoming.header.headerFields[message.HeaderFields.INTERFACE]
        for handler in self.signalHandlers[interfaceName] + self.signalHandlers[None]:
            handler(incoming)

    def close(self):
        self.socket.shutdown(socket.SHUT_RDWR)
        self.socket.close()
