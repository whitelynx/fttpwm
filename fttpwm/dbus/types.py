# -*- cod-ing: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: D-Bus data type system

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from abc import ABCMeta, abstractmethod, abstractproperty
import struct

from StringIO import StringIO


NotSpecified = object()


class Plural(object):
    def __init__(self, value):
        self.value = value

    def __format__(self, fmt):
        return self.value.__format__(fmt)

    @property
    def s(self):
        return '' if self.value == 1 else 's'


class Marshaller(StringIO):
    # Cache of Struct objects to speed up reading and writing messages.
    #TODO: Right now, we're pretty much always writing single values one at a time, instead of combining the message
    # into one larger struct definition and writing it all at once. We'd probably be able to get better performance by
    # combining them first, but this hypothesis should probably also be tested first.
    structFormatters = dict()

    def __init__(self, data=b'', byteOrder=b'='):
        StringIO.__init__(self, data)

        self.byteOrder = byteOrder

    def padSize(self, alignment):
        """Calculate the number of padding bytes required to align the next write to an (alignment)-byte boundary.

        """
        return (alignment - self.tell()) % alignment

    def readPad(self, alignment):
        self.discard(self.padSize(alignment))

    def writePad(self, alignment):
        padSize = self.padSize(alignment)
        if padSize == 0:
            return
        self.write(b'\0' * padSize)  # Write (padSize) null bytes.
        print('{0}: \033[90mWrote {1} byte{1.s} of padding at 0x{2:X}.\033[m'.format(
                self, Plural(padSize), self.tell()))

    def discard(self, size):
        """Skip the next (size) bytes.

        """
        if size == 0:
            return
        print('{0}: \033[33mDiscarding (skipping) {1} byte{1.s} at 0x{2:X}.\033[m'.format(
                self, Plural(size), self.tell()))
        self.seek(size, mode=1)

    def seek(self, pos, mode=0):
        print('{}: \033[34mseek(0x{:X}, {!r}) from 0x{:X}\033[m'.format(self, pos, mode, self.tell()))
        return StringIO.seek(self, pos, mode)

    def skip(self, fmt):
        """Skip bytes equal to the size represented by fmt.

        """
        formatter = self.getStructFormatter(fmt)
        self.discard(formatter.size)

    def writeFiller(self, fmt):
        """Write null bytes equal to the size represented by fmt.

        """
        size = self.getStructFormatter(fmt).size
        if size == 0:
            return
        self.write(b'\0' * size)  # Write (padSize) null bytes.
        print('{0}: \033[33mWrote {1} byte{1.s} of filler at 0x{2:X}.\033[m'.format(self, Plural(size), self.tell()))

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
        packed = formatter.pack(*values)
        self.write(packed)
        print('{0}: \033[32mWrote {1} byte{1.s} of data ({2}) at 0x{3:X}: {4!r}\033[m'.format(
                self, Plural(formatter.size), fmt, self.tell(), packed))

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
        packed = self.read(formatter.size)
        print('{0}: \033[32mRead {1} byte{1.s} of data ({2}) at 0x{3:X}: {4!r}\033[m'.format(
                self, Plural(formatter.size), fmt, self.tell(), packed))
        unpacked = formatter.unpack(packed)

        if len(unpacked) == 1:
            return unpacked[0]
        return unpacked


class SignatureParser(object):
    types = dict()

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


def parseSignatures(signatures):
    return tuple(SignatureParser(signatures))


def parseSignature(signature):
    parsed = parseSignatures(signature)
    assert len(parsed) == 1
    return parsed[0]


class _TypeDefMeta(ABCMeta):
    def __new__(metacls, name, bases, dict):
        cls = ABCMeta.__new__(metacls, name, bases, dict)

        # Register class with the signature parser.
        if len(cls.__abstractmethods__) == 0:
            SignatureParser.types[cls.typeCode] = cls

        return cls


class TypeDef(object):
    __metaclass__ = _TypeDefMeta

    typeCode = abstractproperty()
    structFmt = abstractproperty()
    valueType = abstractproperty()

    @abstractmethod
    def __init__(self):
        super(TypeDef, self).__init__()

        self.defaultValue = NotSpecified

    def __call__(self, value=NotSpecified):
        if value is NotSpecified:
            if self.defaultValue is NotSpecified:
                return self.valueType()

            else:
                return self.defaultValue

        else:
            return self.valueType(value)

    def __repr__(self):
        if self.defaultValue is NotSpecified:
            return '<{}>'.format(self.__class__.__name__)
        else:
            return '<{} default={}>'.format(self.__class__.__name__, self.defaultValue)

    def __unicode__(self):
        return self.__class__.__name__

    @classmethod
    def fromSignature(cls, parser):
        return cls()

    def toSignature(self):
        return self.typeCode

    @property
    def alignment(self):
        return self.size

    @property
    def size(self):
        return struct.calcsize(self.structFmt)

    @abstractmethod
    def writeTo(self, marshaller, data):
        pass

    @abstractmethod
    def readFrom(self, marshaller):
        pass


class BasicTypeDef(TypeDef):
    def __init__(self):
        super(BasicTypeDef, self).__init__()

    def writeTo(self, marshaller, data):
        marshaller.pack(self.structFmt, data)

    def readFrom(self, marshaller):
        return self(marshaller.unpack(self.structFmt))


class IntegerTypeDef(BasicTypeDef):
    valueType = int


class BYTE(IntegerTypeDef):
    """8-bit unsigned integer

    Type code: 121 (ASCII 'y')

    """
    typeCode = b'y'
    structFmt = b'B'

    class _ByteInstance(int):
        def __new__(cls, value=NotSpecified, base=NotSpecified):
            try:
                if value is NotSpecified:
                    return int.__new__(cls)

                elif base is NotSpecified:
                    return int.__new__(cls, value)

                else:
                    return int.__new__(cls, value, base)

            except ValueError:
                return int.__new__(cls, ord(value))

    valueType = _ByteInstance

    def writeTo(self, marshaller, data):
        marshaller.pack(self.structFmt, self.valueType(data))

    def readFrom(self, marshaller):
        return self.valueType(marshaller.unpack(self.structFmt))

Byte = BYTE()


class BOOLEAN(BasicTypeDef):
    """Boolean value, 0 is FALSE and 1 is TRUE. Everything else is invalid.

    Type code: 98 (ASCII 'b')

    """
    typeCode = b'b'
    structFmt = b'xxx?'  # BOOLEAN in the spec is 32-bit, but Python's struct module only uses 8 bits; add padding.
    valueType = bool

Boolean = BOOLEAN()


class INT16(IntegerTypeDef):
    """16-bit signed integer

    Type code: 110 (ASCII 'n')

    """
    typeCode = b'n'
    structFmt = b'h'

Int16 = INT16()


class UINT16(IntegerTypeDef):
    """16-bit unsigned integer

    Type code: 113 (ASCII 'q')

    """
    typeCode = b'q'
    structFmt = b'H'

UInt16 = UINT16()


class INT32(IntegerTypeDef):
    """32-bit signed integer

    Type code: 105 (ASCII 'i')

    """
    typeCode = b'i'
    structFmt = b'i'

Int32 = INT32()


class UINT32(IntegerTypeDef):
    """32-bit unsigned integer

    Type code: 117 (ASCII 'u')

    """
    typeCode = b'u'
    structFmt = b'I'

UInt32 = UINT32()


class INT64(IntegerTypeDef):
    """64-bit signed integer

    Type code: 120 (ASCII 'x')

    """
    typeCode = b'x'
    structFmt = b'q'

Int64 = INT64()


class UINT64(IntegerTypeDef):
    """64-bit unsigned integer

    Type code: 116 (ASCII 't')

    """
    typeCode = b't'
    structFmt = b'Q'

UInt64 = UINT64()


class DOUBLE(BasicTypeDef):
    """IEEE 754 double

    Type code: 100 (ASCII 'd')

    """
    typeCode = b'd'
    structFmt = b'd'
    valueType = float

Double = DOUBLE()


class UNIX_FD(IntegerTypeDef):
    """Unix file descriptor

    Type code: 104 (ASCII 'h')

    """
    typeCode = b'h'
    structFmt = b'I'

UnixFD = UNIX_FD()


class STRING(BasicTypeDef):
    """UTF-8 string (must be valid UTF-8). Must be nul terminated and contain no other nul bytes.

    Type code: 115 (ASCII 's')
    """
    typeCode = b's'
    structFmt = b'I'
    valueType = unicode

    def writeTo(self, marshaller, data):
        marshaller.pack(self.structFmt, len(data))  # String length in bytes, excluding terminating null
        marshaller.write(data.encode('UTF-8'))  # String data
        marshaller.write(b'\0')  # Terminating null byte

    def readFrom(self, marshaller):
        length = marshaller.unpack(self.structFmt)  # String length in bytes, excluding terminating null
        data = marshaller.read(length).decode('UTF-8')
        marshaller.discard(1)  # Discard terminating null byte.
        return self(data)

String = STRING()


class OBJECT_PATH(STRING):
    """Name of an object instance

    Type code: 111 (ASCII 'o')

    """
    typeCode = b'o'

ObjectPath = OBJECT_PATH()


class SIGNATURE(STRING):
    """A type signature

    Type code: 103 (ASCII 'g')

    """
    typeCode = b'g'
    structFmt = b'B'

    def valueType(self, value):
        return parseSignatures(value)

Signature = SIGNATURE()


class ContainerTypeDef(TypeDef):
    def __init__(self, *subtypes):
        for subtype in subtypes:
            if not isinstance(subtype, TypeDef):
                raise TypeError('{}() argument must be a TypeDef, not {!r}'.format(
                    type(self).__name__,
                    type(subtype).__name__)
                    )

        super(ContainerTypeDef, self).__init__()

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

    def toSignature(self):
        return '{}{}{}'.format(
                self.typeCode,
                ''.join(st.toSignature() for st in self.subtypes),
                self.endTypeCode
                )


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
    typeCode = b'a'
    structFmt = b'I'

    def __init__(self, subtype):
        super(ARRAY, self).__init__(subtype)

    @property
    def subtype(self):
        return self.subtypes[0]

    @property
    def valueType(self):
        if isinstance(self.subtype, DICT_ENTRY):
            if isinstance(self.subtype.subtypes[1], VARIANT):
                return VARIANT._VariantDict
            else:
                return dict
        else:
            return list

    @classmethod
    def fromSignature(cls, parser):
        subtype = parser.buildNext()
        return cls(subtype)

    def toSignature(self):
        return '{}{}'.format(self.typeCode, self.subtype.toSignature())

    def writeTo(self, marshaller, data):
        # Support for dictionaries.
        if isinstance(self.subtype, DICT_ENTRY):
            data = data.items()

        placeholderPos = marshaller.tell()

        marshaller.writeFiller(self.structFmt)  # Placeholder for length in bytes
        marshaller.writePad(self.subtype.alignment)  # Padding for contents

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
        marshaller.readPad(self.subtype.alignment)  # Padding for contents

        endPos = marshaller.tell() + length
        items = list(self._readItems(marshaller, endPos))

        return self.valueType(items)


class STRUCT(EnclosedContainerTypeDef):
    """Struct.

    Type code 114 'r' is reserved for use in bindings and implementations to represent the general concept of a struct,
    and must not appear in signatures used on D-Bus.

    Type codes: 114 (ASCII 'r'), 40 (ASCII '('), 41 (ASCII ')')

    """
    typeCode = b'('
    endTypeCode = b')'
    structFmt = b'd'  # Only used to give us 8-byte alignment

    def __init__(self, *subtypes, **kwargs):
        super(STRUCT, self).__init__(*subtypes)

        self._memberNames = kwargs.pop('memberNames', None)

        if len(kwargs) != 0:
            raise TypeError('unrecognized keyword arguments: {}'.format(', '.join(kwargs)))

    def makeOrderedStructInstance(self):
        class _OrderedStructInstance(list):
            def __init__(inst, *values):
                if len(values) < len(self.subtypes):
                    values += tuple(subtype() for subtype in self.subtypes[len(values):])

                super(_OrderedStructInstance, inst).__init__(values)

            def __repr__(inst):
                output = ['Sig(', repr(str(self.toSignature())), ')(']
                output.append(', '.join(map(repr, inst)))
                output.append(')')

                return ''.join(output)

            def __getitem__(inst, index):
                try:
                    return super(_OrderedStructInstance, inst).__getitem__(index)
                except IndexError:
                    raise IndexError("struct index out of range")

            def __setitem__(inst, index, value):
                if index > len(self.subtypes):
                    raise IndexError("struct index out of range")

                super(_OrderedStructInstance, inst).__setitem__(index, value)

        return _OrderedStructInstance

    def makeNamedValueStructInstance(self):
        class _NamedValueStructInstance(object):
            __slots__ = self.memberNames

            def __init__(inst, *values, **namedValues):
                remaining = set(self.memberNames)

                for idx, value in enumerate(values):
                    remaining.remove(self.memberNames[idx])
                    inst[idx] = value

                for key, value in namedValues.iteritems():
                    remaining.remove(key)
                    inst[key] = value

                for key in remaining:
                    inst[key] = self.subtypes[self.memberNames.index(key)]()

            def __repr__(inst):
                output = ['Sig(', repr(str(self.toSignature())), ')(']
                output.append(', '.join('{}={!r}'.format(key, inst[key]) for key in self.memberNames))
                output.append(')')

                return ''.join(output)

            def __getitem__(inst, key):
                try:
                    name = key
                    if not isinstance(key, basestring):
                        name = self.memberNames[key]

                    return getattr(inst, name)

                except IndexError:
                    raise IndexError("struct index {} out of range".format(key))

                except AttributeError:
                    if isinstance(key, basestring):
                        raise AttributeError("no struct member named {}".format(key))
                    else:
                        raise AttributeError("struct member {} has not yet been set".format(self.memberNames[key]))

            def __setitem__(inst, key, value):
                try:
                    if not isinstance(key, basestring):
                        key = self.memberNames[key]

                    setattr(inst, key, value)

                except IndexError:
                    raise IndexError("struct index {} out of range".format(key))

                except AttributeError:
                    raise AttributeError("no struct member named {}".format(key))

        return _NamedValueStructInstance

    @property
    def valueType(self):
        try:
            return self._instanceClass

        except AttributeError:
            if self.memberNames is not None:
                self._instanceClass = self.makeNamedValueStructInstance()
            else:
                self._instanceClass = self.makeOrderedStructInstance()
            return self._instanceClass

    def __call__(self, *values, **namedValues):
        namedValueCount = len(namedValues)
        positionalValueCount = len(values)

        if positionalValueCount + namedValueCount > len(self.subtypes):
            raise TypeError('{cls}.__call__() takes at most {subtypeCount} argument{plural} ({argCount} given)'.format(
                    cls=type(self).__name__,
                    subtypeCount=len(self.subtypes),
                    plural='' if len(self.subtypes) == 1 else 's',
                    argCount=positionalValueCount + namedValueCount
                    ))

        if namedValueCount > 0 and self.memberNames is None:
            raise TypeError('keyword arguments not allowed when no STRUCT member names have been assigned')

        return self.valueType(*values, **namedValues)

    def __getitem__(self, key):
        try:
            if isinstance(key, basestring):
                key = self.memberNames.index(key)

            return self.subtypes[key]

        except IndexError:
            raise IndexError("struct index {} out of range".format(key))

        except ValueError:
            raise KeyError("no struct member named {}".format(key))

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as ex:
            raise AttributeError(ex.message)

    @property
    def memberNames(self):
        return self._memberNames

    @memberNames.setter
    def memberNames(self, names):
        assert len(names) == len(self.subtypes)
        self._memberNames = names

    def writeTo(self, marshaller, data):
        if self.memberNames is not None:
            try:
                data = [
                        getattr(data, name)
                        for name in self.memberNames
                        ]
            except AttributeError:
                pass

        marshaller.writePad(self.alignment)  # Padding for contents

        # Write contents!
        for subtype, item in zip(self.subtypes, data):
            subtype.writeTo(marshaller, item)

    def readFrom(self, marshaller):
        marshaller.readPad(self.alignment)  # Padding for contents

        #print('{} reading subtypes {}'.format(self, self.subtypes))
        return self(*[
                subtype.readFrom(marshaller)
                for subtype in self.subtypes
                ])


class VARIANT(ContainerTypeDef):
    """Variant type (the type of the value is part of the value itself)

    Type code: 118 (ASCII 'v')

    """
    typeCode = b'v'
    structFmt = b'B'  # We don't actually use this, so we just copy the one from SIGNATURE since it's our first member.

    def __init__(self):
        super(VARIANT, self).__init__(Signature)

    class _VariantInstance(object):
        __slots__ = ['type', 'value']

        def __init__(self, type=NotSpecified, value=NotSpecified):
            self.type = type
            self.value = value

        def __repr__(self):
            return '{!s}({!r})'.format(self.type, self.value)

    valueType = _VariantInstance

    class _VariantDict(dict):
        def __getitem__(self, key):
            return super(VARIANT._VariantDict, self).__getitem__(key).value

        def __setitem__(self, key, value):
            if not isinstance(value, VARIANT._VariantInstance):
                type = VARIANT._guessType(value)
                value = VARIANT._VariantInstance(type, value)

            super(VARIANT._VariantDict, self).__setitem__(key, value)

    def __call__(self, type=NotSpecified, value=NotSpecified):
        if type is NotSpecified:
            if self.defaultValue is NotSpecified:
                return self.valueType()

            else:
                return self.defaultValue

        elif value is NotSpecified:
            if self.defaultValue is NotSpecified or self.defaultValue.type != type:
                return self.valueType(type)

            else:
                return self.defaultValue

        else:
            return self.valueType(type, value)

    @classmethod
    def _guessType(self, value):
        #if isinstance(value, bytes):
        #    warnings.warn('Guessing type Signature for a bytes value! Use Variant.valueType() here.',
        #            UnicodeWarning, stacklevel=2)
        #    return Signature
        #elif isinstance(value, unicode):
        #    warnings.warn('Guessing type String for a unicode value! Use Variant.valueType() here.',
        #            UnicodeWarning, stacklevel=2)
        #    return String
        #else:
            raise ValueError("Couldn't guess D-Bus type based on Python value {!r}!".format(value))

    def writeTo(self, marshaller, data):
        self.subtypes[0].writeTo(marshaller, data.type.toSignature())
        data.type.writeTo(marshaller, data.value)

    def readFrom(self, marshaller):
        type = self.subtypes[0].readFrom(marshaller)[0]
        value = type.readFrom(marshaller)
        return self._VariantInstance(type, value)

Variant = VARIANT()


class DICT_ENTRY(STRUCT):
    """Entry in a dict or map (array of key-value pairs).

    Type codes: 101 (ASCII 'e'), 123 (ASCII '{'), 125 (ASCII '}')

    Type code 101 'e' is reserved for use in bindings and implementations to represent the general concept of a dict or
    dict-entry, and must not appear in signatures used on D-Bus.

    """
    typeCode = b'{'
    endTypeCode = b'}'

    def __init__(self, keyType, valueType):
        super(DICT_ENTRY, self).__init__(keyType, valueType)

    @property
    def memberNames(self):
        return self._memberNames

    @memberNames.setter
    def memberNames(self, value):
        raise RuntimeError("Setting memberNames is invalid in a DICT_ENTRY!")
