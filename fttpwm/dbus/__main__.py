# -*- cod-ing: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: D-Bus client test

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import logging

from . import connection


logging.basicConfig(level=logging.NOTSET)

logger = logging.getLogger("fttpwm.dbus.__main__")

bus = connection.SessionBus()
bus.connect()
