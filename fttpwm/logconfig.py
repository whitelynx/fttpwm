# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import
"""FTTPWM: Logging configuration

Copyright (c) 2012-2013 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from datetime import datetime
import logging
import logging.config
import os
import sys


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
#XXX: /HACK


TRACE = 5


class Logger(logging.Logger):
    def trace(self, msg, *args, **kwargs):
        """Log 'msg % args' with severity 'TRACE'.

        """
        if self.isEnabledFor(TRACE):
            self._log(TRACE, msg, args, **kwargs)


class Formatter(logging.Formatter):
    """A Formatter subclass that uses datetime.strftime instead of time.strftime, so the '%f' format (microseconds) is
    supported.

    """
    def formatTime(self, record, datefmt=None):
        created = datetime.fromtimestamp(record.created)
        if datefmt is None:
            return created.isoformat(' ')
        return created.strftime(datefmt)


def configure():
    logging.Formatter = Formatter
    logging.Manager.getLogger = getLogger
    logging.addLevelName(TRACE, 'TRACE')
    logging.setLoggerClass(Logger)

    logConfig = {
            "disable_existing_loggers": False,
            "formatters": {
                "brief": {
                    "datefmt": "%H:%M:%S.%f",
                    "format": "%(asctime)s [%(levelname)-8s] %(name)s:  %(message)s"
                    },
                "colored": {
                    "datefmt": "%H:%M:%S.%f",
                    "format": u"%(asctime)s %(bold)s%(blackFG)s[%(resetTerm)s"
                        u"%(levelColor)s%(levelname)-8s%(resetTerm)s"
                        u"%(bold)s%(blackFG)s]%(resetTerm)s "
                        u"%(cyanFG)s%(name)s%(bold)s%(blackFG)s:%(resetTerm)s  "
                        u"%(faint)s%(italic)s%(message)s%(resetTerm)s"
                    },
                "default": {
                    "datefmt": "%Y-%m-%d %H:%M:%S.%f",
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
                    "level": "DEBUG",
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

    logging.getLogger('logconfig').debug('Logging configured and monkeypatched.')
