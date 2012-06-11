import logging
import sys

from .. import singletons


logger = logging.getLogger("fttpwm.bindings.wm")


def switchWorkspace(ws):
    """Switches to the given workspace.

    """
    def switchWorkspace_(*event):
        logger.debug("Switching to workspace %r", ws)
        singletons.wm.workspaces.switchTo(ws)

    return switchWorkspace_


def quit(*event):
    logger.debug("Exiting.")
    singletons.x.exit()
