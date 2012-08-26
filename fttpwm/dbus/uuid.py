import binascii
import os
import struct
import time


# From the spec:
#   The term "UUID" in this document is intended literally, i.e. an identifier that is universally unique. It is not
#   intended to refer to RFC4122, and in fact the D-Bus UUID is not compatible with that RFC.
#
#   The UUID must contain 128 bits of data and be hex-encoded. The hex-encoded string may not contain hyphens or other
#   non-hex-digit characters, and it must be exactly 32 characters long. To generate a UUID, the current reference
#   implementation concatenates 96 bits of random data followed by the 32-bit time in seconds since the UNIX epoch (in
#   big endian byte order)."
def generateUUID():
    """Generate a D-Bus-compatible UUID.

    Note that these are NOT compatible with the UUIDs described in RFC4122. (see the standard 'uuid' module for that)

    """
    return binascii.hexlify(struct.pack(
            '>12sI',
            os.urandom(12),  # 96 bits (12 bytes) of random data
            time.time()
            ))
