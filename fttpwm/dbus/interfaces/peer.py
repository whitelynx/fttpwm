# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: D-Bus Peer interface

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import logging

from ..interface import DBusInterface, Method


logger = logging.getLogger("fttpwm.dbus.interfaces.peer")


class Peer(DBusInterface('org.freedesktop.DBus.Peer')):
    """Represents a single peer (application) on a connection or bus.

    The reference implementation handles this interface's implementation automatically. FTTPWM's implementation should
    do the same eventually. It is probably not useful to ever actually implement this interface outside of the core
    implementation.

    """
    @Method()
    def Ping(self):
        """Should do nothing other than reply with a METHOD_RETURN as usual. It does not matter which object path a
        ping is sent to.

        """

    @Method(outSig='s')
    def GetMachineId(self):
        """Should reply with a METHOD_RETURN containing a hex-encoded UUID representing the identity of the machine the
        process is running on. This UUID must be the same for all processes on a single system at least until that
        system next reboots. It should be the same across reboots if possible, but this is not always possible to
        implement and is not guaranteed. It does not matter which object path a GetMachineId is sent to.

        """
