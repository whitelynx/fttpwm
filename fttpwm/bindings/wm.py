import logging
import sys

from .. import wm


logger = logging.getLogger("fttpwm.bindings.wm")


def switchWorkspace(ws):
    """Switches to the given workspace.

    """
    def switchWorkspace_(*event):
        logger.debug("Switching to workspace %r", ws)
        wm.WM.instance.workspaces.switchTo(ws)

    return switchWorkspace_


def quit(*event):
    logger.debug("Exiting.")
    sys.exit(0)
