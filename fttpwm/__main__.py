# -*- cod ing: utf-8 -*-
from __future__ import unicode_literals, absolute_import
"""FTTPWM: Main application

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import logging

from . import logconfig


logconfig.configure()

logger = logging.getLogger("fttpwm")


from .x import XConnection
from .wm import WM

try:
    from .eventloop.zmq_loop import ZMQEventLoop

    eventloop = ZMQEventLoop()
    logger.info("Using the ZeroMQ event loop.")

except ImportError:
    logger.warn("Couldn't import zmq! Falling back to polling event loop.", exc_info=True)

    from .eventloop.poll_loop import PollEventLoop

    eventloop = PollEventLoop()


x = XConnection()
WM()
eventloop.run()
