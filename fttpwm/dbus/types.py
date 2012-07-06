# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: D-Bus data type system

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from abc import ABCMeta, abstractmethod, abstractproperty
import struct

from StringIO import StringIO

"""
BYTE	A single 8-bit byte.	1
BOOLEAN	As for UINT32, but only 0 and 1 are valid values.	4
INT16	16-bit signed integer in the message's byte order.	2
UINT16	16-bit unsigned integer in the message's byte order.	2
INT32	32-bit signed integer in the message's byte order.	4
UINT32	32-bit unsigned integer in the message's byte order.	4
INT64	64-bit signed integer in the message's byte order.	8
UINT64	64-bit unsigned integer in the message's byte order.	8
DOUBLE	64-bit IEEE 754 double in the message's byte order.	8

UNIX_FD	32-bit unsigned integer in the message's byte order. The actual file descriptors need to be transferred out-of-band via some platform specific mechanism. On the wire, values of this type store the index to the file descriptor in the array of file descriptors that accompany the message.	4

STRING	A UINT32 indicating the string's length in bytes excluding its terminating nul, followed by non-nul string data of the given length, followed by a terminating nul byte.	 4 (for the length)

OBJECT_PATH	Exactly the same as STRING except the content must be a valid object path (see below).	 4 (for the length)

SIGNATURE	The same as STRING except the length is a single byte (thus signatures have a maximum length of 255) and the content must be a valid signature (see below).	 1

ARRAY	 A UINT32 giving the length of the array data in bytes, followed by alignment padding to the alignment boundary of the array element type, followed by each array element. The array length is from the end of the alignment padding to the end of the last element, i.e. it does not include the padding after the length, or any padding after the last element. Arrays have a maximum length defined to be 2 to the 26th power or 67108864. Implementations must not send or accept arrays exceeding this length.	 4 (for the length)

STRUCT	 A struct must start on an 8-byte boundary regardless of the type of the struct fields. The struct value consists of each field marshaled in sequence starting from that 8-byte alignment boundary.	 8

VARIANT	 A variant type has a marshaled SIGNATURE followed by a marshaled value with the type given in the signature. Unlike a message signature, the variant signature can contain only a single complete type. So "i", "ai" or "(ii)" is OK, but "ii" is not. Use of variants may not cause a total message depth to be larger than 64, including other container types such as structures.	 1 (alignment of the signature)

DICT_ENTRY	 Identical to STRUCT.	 8

"""


class Marshaller(StringIO):
    structFormatters = dict()

    def __init__(self, data='', byteOrder='='):
        super(Marshaller, self).__init__(data)

        self.byteOrder = byteOrder

    def padSize(self, alignment):
        """Calculate the number of padding bytes required to align the next write to an (alignment)-byte boundary.

        """
        return (alignment - self.tell()) % alignment

    def readPad(self, alignment):
        self.discard(self.padSize(alignment))

    def writePad(self, alignment):
        self.write('\0' * self.padSize(alignment))  # Write (padSize) null bytes.

    def discard(self, size):
        """Skip the next (size) bytes.

        """
        self.seek(size, mode=1)

    def getStructFormatter(self, fmt):
        fmt = self.byteOrder + fmt
        try:
            return self.structFormatters[fmt]
        except KeyError:
            self.structFormatters[fmt] = struct.Struct(fmt)
            return self.structFormatters[fmt]

    def pack(self, fmt, *values, **kwargs):
        """Write one or more values using the given format and alignment.

        """
        formatter = self.getStructFormatter(fmt)
        alignment = kwargs.pop('alignment', formatter.size)

        if kwargs:
            raise TypeError("Unrecognized keyword arguments!", kwargs)

        # Add any padding required to align the value(s).
        self.writePad(alignment)

        # Write the value(s).
        self.write(formatter.pack(*values))

    def unpack(self, fmt, **kwargs):
        """Read one or more values using the given format and alignment.

        """
        formatter = self.getStructFormatter(fmt)
        alignment = kwargs.pop('alignment', formatter.size)

        if kwargs:
            raise TypeError("Unrecognized keyword arguments!", kwargs)

        # Skip any padding required to align the value(s).
        self.readPad(alignment)

        # Read the value(s).
        unpacked = formatter.unpack(self.read(formatter.size))

        if len(unpacked) == 1:
            return unpacked[0]
        return unpacked


class SignatureParser(object):
    def __init__(self, signature):
        self.signature = self.remaining = signature

    def __iter__(self):
        while len(self.remaining) > 0:
            yield self.buildNext()

    def peek(self):
        return self.remaining[0]

    def consume(self):
        nextCode = self.remaining[0]
        self.remaining = self.remaining[1:]
        return nextCode

    def buildNext(self):
        typeCode = self.consume()
        nextType = self.types[typeCode]
        return nextType.fromSignature(self)


def parseSignatures(signature):
    return tuple(*SignatureParser(signature))


def parseSignature(signature):
    parsed = parseSignatures(signature)
    assert len(parsed) == 0
    return parsed[0]


class TypeDef(object):
    __metaclass__ = ABCMeta

    typeCode = abstractproperty()
    structFmt = abstractproperty()

    @abstractmethod
    def __init__(self):
        super(TypeDef, self).__init__()

    @abstractmethod
    @classmethod
    def fromSignature(cls, parser):
        pass

    @property()
    def alignment(self):
        return self.size

    @abstractmethod
    def writeTo(self, marshaller, data):
        pass

    @abstractmethod
    def readFrom(self, marshaller):
        pass


class BasicTypeDef(TypeDef):
    @classmethod
    def fromSignature(cls, parser):
        return cls()

    def writeTo(self, marshaller, data):
        marshaller.pack(self.structFmt, data)

    def readFrom(self, marshaller):
        return marshaller.unpack(self.structFmt)


class BYTE(BasicTypeDef):
    """8-bit unsigned integer

    Type code: 121 (ASCII 'y')

    """
    typeCode = 'y'
    structFmt = 'B'


class BOOLEAN(BasicTypeDef):
    """Boolean value, 0 is FALSE and 1 is TRUE. Everything else is invalid.

    Type code: 98 (ASCII 'b')

    """
    typeCode = 'b'
    structFmt = 'xxx?'  # BOOLEAN in the D-Bus spec is 32-bit, but Python's struct module only uses 8 bits; add padding


class INT16(BasicTypeDef):
    """16-bit signed integer

    Type code: 110 (ASCII 'n')

    """
    typeCode = 'n'
    structFmt = 'h'


class UINT16(BasicTypeDef):
    """16-bit unsigned integer

    Type code: 113 (ASCII 'q')

    """
    typeCode = 'q'
    structFmt = 'H'


class INT32(BasicTypeDef):
    """32-bit signed integer

    Type code: 105 (ASCII 'i')

    """
    typeCode = 'i'
    structFmt = 'i'


class UINT32(BasicTypeDef):
    """32-bit unsigned integer

    Type code: 117 (ASCII 'u')

    """
    typeCode = 'u'
    structFmt = 'I'


class INT64(BasicTypeDef):
    """64-bit signed integer

    Type code: 120 (ASCII 'x')

    """
    typeCode = 'x'
    structFmt = 'q'


class UINT64(BasicTypeDef):
    """64-bit unsigned integer

    Type code: 116 (ASCII 't')

    """
    typeCode = 't'
    structFmt = 'Q'


class DOUBLE(BasicTypeDef):
    """IEEE 754 double

    Type code: 100 (ASCII 'd')

    """
    typeCode = 'd'
    structFmt = 'd'


class UNIX_FD(BasicTypeDef):
    """Unix file descriptor

    Type code: 104 (ASCII 'h')

    """
    typeCode = 'h'
    structFmt = 'I'


class STRING(BasicTypeDef):
    """UTF-8 string (must be valid UTF-8). Must be nul terminated and contain no other nul bytes.

    Type code: 115 (ASCII 's')
    """
    typeCode = 's'
    structFmt = 'I'

    def writeTo(self, marshaller, data):
        marshaller.pack(self.structFmt, len(data))  # String length in bytes, excluding terminating null
        marshaller.write(data)  # String data
        marshaller.write('\0')  # Terminating null byte

    def readFrom(self, marshaller):
        length = marshaller.unpack(self.structFmt)  # String length in bytes, excluding terminating null
        data = marshaller.read(length)
        marshaller.discard(1)  # Discard terminating null byte.
        return data


class OBJECT_PATH(STRING):
    """Name of an object instance

    Type code: 111 (ASCII 'o')

    """
    typeCode = 'o'


class SIGNATURE(STRING):
    """A type signature

    Type code: 103 (ASCII 'g')

    """
    typeCode = 'g'
    structFmt = 'B'


class ContainerTypeDef(TypeDef):
    def __init__(self, *subtypes):
        self.subtypes = subtypes


class EnclosedContainerTypeDef(ContainerTypeDef):
    endTypeCode = abstractproperty()

    @classmethod
    def fromSignature(cls, parser):
        subtypes = list()

        while parser.peek() != cls.endTypeCode:
            subtypes.append(parser.buildNext())

        assert parser.consume() == cls.endTypeCode

        return cls(*subtypes)


class ARRAY(ContainerTypeDef):
    """Array

    A UINT32 giving the length of the array data in bytes, followed by alignment padding to the alignment boundary of
    the array element type, followed by each array element. The array length is from the end of the alignment padding
    to the end of the last element, i.e. it does not include the padding after the length, or any padding after the
    last element. Arrays have a maximum length defined to be 2 to the 26th power or 67108864. Implementations must
    not send or accept arrays exceeding this length.

    Alignment: 4 (for the length)

    Type code: 97 (ASCII 'a')

    """
    typeCode = 'a'
    structFmt = 'I'

    def __init__(self, subtype):
        super(ARRAY, self).__init__(subtype)
        self.subtype = subtype

    def writeTo(self, marshaller, data):
        # Support for dictionaries.
        if isinstance(self.subtype, DICT_ENTRY):
            data = data.items()

        placeholderPos = marshaller.tell()

        marshaller.skip(self.structFmt)  # Placeholder for length in bytes
        self.writePad(self.subtype.alignment)  # Padding for contents

        startPos = marshaller.tell()

        # Write contents!
        for item in data:
            self.subtype.writeTo(marshaller, item)

        endPos = marshaller.tell()

        marshaller.seek(placeholderPos)
        marshaller.pack(self.structFmt, endPos - startPos)  # Overwrite placeholder with actual length in bytes

        marshaller.seek(endPos)  # Return to end position

    def _readItems(self, marshaller, endPos):
        while marshaller.tell() < endPos:
            yield self.subtype.readFrom(marshaller)

    def readFrom(self, marshaller):
        length = marshaller.unpack(self.structFmt)  # Array length in bytes
        self.readPad(self.subtype.alignment)  # Padding for contents

        startPos = marshaller.tell()
        endPos = startPos + length

        data = list(self._readItems(marshaller, endPos))

        # Support for dictionaries.
        if isinstance(self.subtype, DICT_ENTRY):
            return dict(data)

        return data


class STRUCT(ContainerTypeDef):
    """Struct.

    Type code 114 'r' is reserved for use in bindings and implementations to represent the general concept of a struct,
    and must not appear in signatures used on D-Bus.

    Type codes: 114 (ASCII 'r'), 40 (ASCII '('), 41 (ASCII ')')

    """
    typeCode = '('
    endTypeCode = ')'
    structFmt = 'd'  # Only used to give us 8-byte alignment

    def __init__(self, *subtypes):
        super(VARIANT, self).__init__(subtypes)
        self._memberNames = None

    @property
    def memberNames(self):
        return self._memberNames

    @memberNames.setter
    def memberNames(self, value):
        assert len(value) == len(self.subtypes)
        self._memberNames = value

    def writeTo(self, marshaller, data):
        if self.memberNames is not None:
            try:
                data = [
                        getattr(data, name)
                        for name in self.memberNames
                        ]
            except AttributeError:
                pass

        self.writePad(self.alignment)  # Padding for contents

        # Write contents!
        for subtype, item in zip(self.subtypes, data):
            subtype.writeTo(marshaller, item)

    def readFrom(self, marshaller):
        self.readPad(self.alignment)  # Padding for contents

        return tuple(
                subtype.readFrom(marshaller)
                for subtype in self.subtypes
                )


class VARIANT(ContainerTypeDef):
    """Variant type (the type of the value is part of the value itself)

    Type code: 118 (ASCII 'v')

    """
    typeCode = 'v'

    def __init__(self):
        super(VARIANT, self).__init__()


class DICT_ENTRY(STRUCT):
    """Entry in a dict or map (array of key-value pairs).

    Type codes: 101 (ASCII 'e'), 123 (ASCII '{'), 125 (ASCII '}')

    Type code 101 'e' is reserved for use in bindings and implementations to represent the general concept of a dict or
    dict-entry, and must not appear in signatures used on D-Bus.

    """
    typeCode = '{'
    endTypeCode = '}'

    def __init__(self, keyType, valueType):
        super(DICT_ENTRY, self).__init__(keyType, valueType)

    @property
    def memberNames(self):
        return self._memberNames

    @memberNames.setter
    def memberNames(self, value):
        raise RuntimeError("Setting memberNames is invalid in a DICT_ENTRY!")
