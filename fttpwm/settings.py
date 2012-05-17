from argparse import Namespace
from os.path import expanduser, join, dirname, exists
import logging


logger = logging.getLogger("fttpwm.settings")


defaultRcFileLocations = (
        expanduser("~/.fttpwmrc.py"),
        "/etc/fttpwmrc.py",
        join(dirname(__file__), "default_fttpwmrc.py")
        )


settings = Namespace()


def loadSettings(filenames=defaultRcFileLocations):
    global settings
    for filename in filenames:
        if exists(filename):
            settingsFile = filename

    settings = {}

    # Load settings
    execfile(settingsFile, globals={}, locals=settings)

    settings = Namespace(settings)
