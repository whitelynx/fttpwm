import logging

import xpybutil
import xpybutil.event as event
import xpybutil.mousebind as mousebind

from .bind import processBinding
from .settings import settings


logger = logging.getLogger("fttpwm.mouse")

captureCallbacks = []


def bindMouse(bindings):
    for buttonString, binding in bindings.iteritems():
        binding = processBinding(binding)

        mods, button = mousebind.parse_buttonstring(buttonString)
        if not mousebind.grab_button(xpybutil.root, mods, button).status:
            logger.error("Couldn't grab mouse button %r!", buttonString)
            return

        if binding.onPress is not None:
            event.connect('ButtonPress', xpybutil.root, binding.onPress)

        if binding.onRelease is not None:
            event.connect('ButtonRelease', xpybutil.root, binding.onRelease)

        if binding.onMotion is not None:
            event.connect('MotionNotify', xpybutil.root, binding.onMotion)
