# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: Main application

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import logging
import logging.config
import os
import sys

from .wm import WM


#XXX: HACK: Horrible monkeypatching to work around broken behavior in python's logging module.
def getLogger(self, name):
    """
    Get a logger with the specified name (channel name), creating it
    if it doesn't yet exist. This name is a dot-separated hierarchical
    name, such as "a", "a.b", "a.b.c" or similar.

    If a PlaceHolder existed for the specified name [i.e. the logger
    didn't exist but a child of it did], replace it with the created
    logger and fix up the parent/child references which pointed to the
    placeholder to now point to the logger.
    """
    rv = None
    if not isinstance(name, basestring):
        raise TypeError('A logger name must be string or Unicode')
    #XXX: NO! Bad! If you do this, the formatter will _always_ fail if there are any non-ASCII characters in name.
    #if isinstance(name, unicode):
    #    name = name.encode('utf-8')
    logging._acquireLock()
    try:
        if name in self.loggerDict:
            rv = self.loggerDict[name]
            if isinstance(rv, logging.PlaceHolder):
                ph = rv
                rv = (self.loggerClass or logging._loggerClass)(name)
                rv.manager = self
                self.loggerDict[name] = rv
                self._fixupChildren(ph, rv)
                self._fixupParents(rv)
        else:
            rv = (self.loggerClass or logging._loggerClass)(name)
            rv.manager = self
            self.loggerDict[name] = rv
            self._fixupParents(rv)
    finally:
        logging._releaseLock()
    return rv


logging.Manager.getLogger = getLogger
#XXX: /HACK


logConfig = {
        "disable_existing_loggers": False,
        "formatters": {
            "brief": {
                "datefmt": "%H:%M:%S",
                "format": "%(asctime)s [%(levelname)-8s] %(name)s:  %(message)s"
                },
            "colored": {
                "datefmt": "%H:%M:%S",
                "format": u"%(asctime)s %(bold)s%(blackForeground)s[%(resetTerm)s"
                    u"%(levelColor)s%(levelname)-8s%(resetTerm)s"
                    u"%(bold)s%(blackForeground)s]%(resetTerm)s "
                    u"%(cyanForeground)s%(name)s%(bold)s%(blackForeground)s:%(resetTerm)s  "
                    u"%(faint)s%(italic)s%(message)s%(resetTerm)s"
                },
            "default": {
                "datefmt": "%Y-%m-%d %H:%M:%S",
                "format": "%(asctime)s [%(levelname)-8s] %(name)s:  %(message)s"
                }
            },
        "handlers": {
            "basicConsole": {
                "class": "logging.StreamHandler",
                "formatter": "brief",
                "stream": "ext://sys.stdout"
                },
            "colorConsole": {
                "class": "fttpwm.colorlog.ColoredConsoleHandler",
                "formatter": "colored",
                "level": "NOTSET",
                "stream": "ext://sys.stdout"
                },
            "file": {
                "backupCount": 3,
                "class": "logging.handlers.RotatingFileHandler",
                "filename": os.path.expanduser("~/.fttpwm.log"),
                "formatter": "default",
                "maxBytes": 1073741824
                }
            },
        "root": {
            "handlers": [
                "basicConsole",
                "file"
                ],
            "level": 0
            },
        "version": 1
        }

# If we're running on a normal TTY, use colored log output. (otherwise, we default to the basic non-colored output)
if os.isatty(sys.stdout.fileno()):
    logConfig["root"]["handlers"] = ["colorConsole", "file"]

logging.config.dictConfig(logConfig)


logger = logging.getLogger("fttpwm")


WM().run()
