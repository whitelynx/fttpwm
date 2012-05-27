# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: Main application

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import logging

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


# Monochrome logging
#logging.basicConfig(level=logging.NOTSET, datefmt="%H:%M:%S",
#        format="%(asctime)s[%(levelname)-8s] %(name)s:  %(message)s")

# Color logging (*NIX only)
logging.basicConfig(level=logging.NOTSET,
        datefmt="%H:%M:%S",
        format="%(asctime)s {e}90m[{e}0;1m%(levelname)-8s{e}0;90m]{e}m {e}36m%(name)s{e}90m:{e}m  "
            "{e}2;3m%(message)s{e}m".format(e='\033[')
        )


logger = logging.getLogger("fttpwm")


WM().run()
