# -*- cod-ing: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: D-Bus message implementation

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import logging
import struct
import sys

from .errors import NotEnoughData
from .types import Marshaller, parseSignature, parseSignatures, Signature, Variant


logger = logging.getLogger('fttpwm.dbus.message')


class Types(object):
    # This is an invalid type.
    INVALID = 0

    # Method call.
    METHOD_CALL = 1

    # Method reply with returned data.
    METHOD_RETURN = 2

    # Error reply. If the first argument exists and is a string, it is an error message.
    ERROR = 3

    # Signal emission.
    SIGNAL = 4


class Flags(object):
    # This message does not expect method return replies or error replies; the reply can be omitted as an optimization.
    # However, it is compliant with this specification to return the reply despite this flag and the only harm from
    # doing so is extra network traffic.
    NO_REPLY_EXPECTED = 0x1

    # The bus must not launch an owner for the destination name in response to this message.
    NO_AUTO_START = 0x2


class HeaderFields(object):
    # N/A	not allowed	Not a valid field name (error if it appears in a message)
    INVALID = 0

    # OBJECT_PATH	METHOD_CALL, SIGNAL	The object to send a call to, or the object a signal is emitted from. The
    # special path /org/freedesktop/DBus/Local is reserved; implementations should not send messages with this path,
    # and the reference implementation of the bus daemon will disconnect any application that attempts to do so.
    PATH = 1

    # STRING	SIGNAL	 The interface to invoke a method call on, or that a signal is emitted from. Optional for
    # method calls, required for signals. The special interface org.freedesktop.DBus.Local is reserved; implementations
    # should not send messages with this interface, and the reference implementation of the bus daemon will disconnect
    # any application that attempts to do so.
    INTERFACE = 2

    # STRING	METHOD_CALL, SIGNAL	The member, either the method name or signal name.
    MEMBER = 3

    # STRING	ERROR	The name of the error that occurred, for errors
    ERROR_NAME = 4

    # UINT32	ERROR, METHOD_RETURN	The serial number of the message this message is a reply to. (The serial number
    # is the second UINT32 in the header.)
    REPLY_SERIAL = 5

    # STRING	optional	The name of the connection this message is intended for. Only used in combination with the
    # message bus, see the section called "Message Bus Specification".
    DESTINATION = 6

    # STRING	optional	Unique name of the sending connection. The message bus fills in this field so it is
    # reliable; the field is only meaningful in combination with the message bus.
    SENDER = 7

    # SIGNATURE	optional	The signature of the message body. If omitted, it is assumed to be the empty signature ""
    # (i.e. the body must be 0-length).
    SIGNATURE = 8

    # UINT32	optional	The number of Unix file descriptors that accompany the message. If omitted, it is assumed
    # that no Unix file descriptors accompany the message. The actual file descriptors need to be transferred via
    # platform specific mechanism out-of-band. They must be sent at the same time as part of the message itself. They
    # may not be sent before the first byte of the message itself is transferred or after the last byte of the message
    # itself.
    UNIX_FDS = 9


class Message(object):
    # According to the spec, the header's signature should be "yyyyuua(yv)", but this is more convenient for a couple
    # of reasons:
    # - Wrapping the entire signature in a struct makes it easier to parse as one chunk.
    # - Using a DICT_ENTRY instead of a STRUCT for the header fields allows us to return a dict instead of a list of
    #   tuples, which makes it easier to work with.
    headerType = parseSignature('(yyyyuua{yv})')

    headerType.memberNames = (
            # 1st BYTE - Endianness flag; ASCII 'l' for little-endian or ASCII 'B' for big-endian.
            # Both header and body are in this endianness.
            'byteOrder',

            # 2nd BYTE - Message type. Unknown types must be ignored. See the Types class for possible values.
            'messageType',

            # 3rd BYTE - Bitwise OR of flags. Unknown flags must be ignored. See the Flags class for possible values.
            'flags',

            # 4th BYTE - Major protocol version of the sending application. If the major protocol version of the
            # receiving application does not match, the applications will not be able to communicate and the D-Bus
            # connection must be disconnected. The major protocol version for this version of the specification is 1.
            'protocolVersion',

            # 1st UINT32 - Length in bytes of the message body, starting from the end of the header. The header ends
            # after its alignment padding to an 8-boundary.
            'length',

            # 2nd UINT32 - The serial of this message, used as a cookie by the sender to identify the reply
            # corresponding to this request. This must not be zero.
            'serial',

            # ARRAY of STRUCT of (BYTE,VARIANT) - An array of zero or more header fields where the byte is the field
            # code, and the variant is the field value. The message type determines which fields are required. See the
            # HeaderFields class for possible values.
            # NOTE: In this implementation, the headers are interpreted as a dictionary. (ARRAY of DICT_ENTRY)
            'headerFields',
            )

    headerType.protocolVersion.defaultValue = 1

    _lastSerial = 0

    def __init__(self, bodyTypes='', body=[], header=None):
        self.bodyTypes = bodyTypes

        self.body = body

        if header is None:
            self.header = self.headerType()

            if sys.byteorder == 'little':
                self.header.byteOrder = b'l'
            else:
                self.header.byteOrder = b'B'

        else:
            self.header = header

    def __repr__(self):
        return 'Message({})(...)'.format(
                ', '.join(
                    '{}={!r}'.format(key, self.header[key])
                    for key in self.headerType.memberNames
                    )
                )

    @property
    def bodyTypes(self):
        return self._bodyTypes

    @bodyTypes.setter
    def bodyTypes(self, value):
        if isinstance(value, basestring):
            self._bodyTypes = parseSignatures(value)
        elif hasattr(value, '__iter__'):
            self._bodyTypes = value
        else:
            self._bodyTypes = (value, )
        logger.trace("_bodyTypes={}".format(self._bodyTypes))

    @property
    def bodySignature(self):
        return Variant(Signature, ''.join(bt.toSignature() for bt in self.bodyTypes))

    @classmethod
    def parseFile(cls, file):
        pos = file.tell()
        endianFlag = file.read(1)

        if endianFlag == '':
            raise NotEnoughData

        logger.debug("Seeking back to position %r", pos)
        file.seek(pos)

        logger.debug("endianFlag=%r", endianFlag)
        if endianFlag in (b'l', ord(b'l')):
            byteOrder = b'<'  # Little endian
        elif endianFlag in (b'B', ord(b'B')):
            byteOrder = b'>'  # Big endian
        else:
            pos = file.tell()
            logger.error("Got unrecognized endianness flag for incoming message: %r; all available data: %r",
                    endianFlag, file.read())
            file.seek(pos)
            raise ValueError('Unrecognized endianness flag {!r}!'.format(endianFlag))

        return cls.parseFromMarshaller(Marshaller(file, byteOrder))

    @classmethod
    def parseString(cls, data):
        data = bytes(data)
        if data[0] in (b'l', ord(b'l')):
            byteOrder = b'<'  # Little endian
        elif data[0] in (b'B', ord(b'B')):
            byteOrder = b'>'  # Big endian
        else:
            raise ValueError('Unrecognized endianness flag {!r}!'.format(data[0]))

        return cls.parseFromMarshaller(Marshaller(data, byteOrder))

    @classmethod
    def parseFromMarshaller(cls, marshaller):
        try:
            logger.trace("Reading header...")
            try:
                header = cls.headerType.readFrom(marshaller)
            except struct.error:
                raise NotEnoughData

            marshaller.readPad(8)

            # Make sure we have enough data to read the whole message.
            bodyStart = marshaller.tell()
            marshaller.seek(bodyStart + header.length)

            if marshaller.tell() != bodyStart + header.length:
                raise NotEnoughData

            marshaller.seek(bodyStart)

            bodyTypes = header.headerFields[HeaderFields.SIGNATURE]
            logger.trace("Reading body...")
            body = [bodyType.readFrom(marshaller) for bodyType in bodyTypes]

        finally:
            logger.trace('Ended reading at byte 0x{:X}'.format(marshaller.tell()))
            marshaller.close()

        return Message(bodyTypes, body, header)

    def render(self, target=None):
        if self.header.byteOrder in (b'l', ord(b'l')):
            byteOrder = b'<'
        else:
            byteOrder = b'>'

        bodyMarshaller = Marshaller(byteOrder=byteOrder)
        marshaller = Marshaller(target, byteOrder=byteOrder)

        try:
            # Write the body to its own marshaller so we can determine its length.
            logger.trace("Rendering body...")
            for idx, bodyType in enumerate(self.bodyTypes):
                bodyType.writeTo(bodyMarshaller, self.body[idx])

            # Update header
            Message._lastSerial += 1
            self.header.serial = Message._lastSerial

            self.header.length = bodyMarshaller.tell()
            self.header.headerFields[HeaderFields.SIGNATURE] = self.bodySignature

            # Write to the main marshaller.
            logger.trace("Rendering header...")
            assert marshaller.file.tell() == 0
            self.headerType.writeTo(marshaller, self.header)
            marshaller.writePad(8)
            logger.trace("Header ends at 0x{:X}; copying body after header...".format(marshaller.tell()))
            marshaller.write(bodyMarshaller.file.getvalue())

            if target is None:
                logger.trace("Rendered message: {!r}".format(marshaller.file.getvalue()))
                return marshaller.file.getvalue()

        except IndexError:
            raise RuntimeError("Message can't be rendered unless a full body is set!")

        finally:
            bodyMarshaller.close()
            logger.trace('Ended writing at byte 0x{:X}'.format(marshaller.tell()))
            logger.debug('Rendered message: %r', self)
            marshaller.close()
