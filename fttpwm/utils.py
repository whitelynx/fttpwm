import logging
import shlex
import struct
import subprocess
import sys


logger = logging.getLogger("fttpwm.utils")


def run(*command, **kwargs):
    """Run the given command, returning the new process's PID.

    Additional options may be passed to the Popen constructor through `kwargs`.

    """
    if len(command) == 1 and isinstance(command[0], basestring):
        command = shlex.split(command[0])

    logger.debug("Starting application: %r", command)
    return subprocess.Popen(command, close_fds=True, **kwargs).pid


def startApp(*command, **kwargs):
    """Starts the given command using 'run' in response to a key or button press event.

    Additional options may be passed to the Popen constructor through `kwargs`.

    """
    def startApp_(*event):
        run(*command, **kwargs)

    return startApp_


def convertAttributes(attributes):
    attribMask = 0
    attribValues = list()

    # Values must be sorted by CW enum value, ascending.
    # Luckily, the tuples we get from dict.iteritems will automatically sort correctly.
    for attrib, value in sorted(attributes.iteritems()):
        attribMask |= attrib
        attribValues.append(value)

    return attribMask, attribValues


def findCurrentVisual(screen, desiredDepth, visualID):
    """Find the VISUALTYPE object for our current visual.

    This is needed for initializing a Cairo XCBSurface.

    """
    for depth in screen.allowed_depths:
        if depth.depth == desiredDepth:
            for visual in depth.visuals:
                if visual.visual_id == visualID:
                    return visual


def quit(*event):
    logger.debug("Exiting.")
    sys.exit(0)


def signedToUnsigned16(signed):
    # Pack as a signed int, then unpack that as unsigned.
    return struct.unpack('!I', struct.pack('!i', signed))[0]
