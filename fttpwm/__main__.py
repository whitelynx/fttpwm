"""FTTPWM: Main application

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import logging

import xpybutil
import xpybutil.event as event
#import xpybutil.ewmh as ewmh

from .settings import settings


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

setup = xpybutil.conn.get_setup()
root = setup.roots[0].root
depth = setup.roots[0].root_depth
visual = setup.roots[0].root_visual

window = xpybutil.conn.generate_id()
pid = xpybutil.conn.generate_id()


settings.loadSettings()

event.main()
