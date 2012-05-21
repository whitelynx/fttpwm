"""FTTPWM: Main application

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import logging

from .wm import WM


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
