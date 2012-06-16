import logging
import operator

import xcb

import xpybutil
import xpybutil.keybind as keybind

from .bindings import processBinding, EventClassFilter
from .settings import settings


logger = logging.getLogger("fttpwm.keyboard")

captureCallbacks = []

keybind.get_keyboard_mapping()

settings.setDefaults(
        ignoredModifiers=reduce(operator.or_, keybind.TRIVIAL_MODS)
        )


def bindKeys(bindings):
    for keyString, binding in bindings.iteritems():
        binding = processBinding(binding)
        keyString = keyString.replace('+', '-')

        logger.debug("Binding key %r.", keyString)

        if binding.onPress is not None:
            logger.debug("Binding KeyPress event to onPress (%r)", binding.onPress)
            if not keybind.bind_global_key('KeyPress', keyString,
                    EventClassFilter(xcb.xproto.KeyPressEvent, binding.onPress)):
                logger.error("Couldn't bind key press %s to %r!", keyString, binding.onPress)

        if binding.onRelease is not None:
            logger.debug("Binding KeyRelease event to onRelease (%r)", binding.onRelease)
            if not keybind.bind_global_key('KeyRelease', keyString,
                    EventClassFilter(xcb.xproto.KeyReleaseEvent, binding.onRelease)):
                logger.error("Couldn't bind key release %s to %r!", keyString, binding.onRelease)


class GetCharacterCallback(object):
    def __init__(self, callback, range=None):
        self.callback = callback
        self.range = range

    def __call__(self, keycode, keysym):
        letter = keybind.get_keysym_string(keysym)
        if len(letter) == 1 and (self.range is None or ord(letter) in self.range):
            self.callback(letter.lower())
            return False
        return True


def captureKeypresses(callback):
    global captureCallbacks

    GS = xcb.xproto.GrabStatus
    if keybind.grab_keyboard(xpybutil.root).status == GS.Success:
        captureCallbacks.append(callback)


def captureLetter(callback):
    captureKeypresses(GetCharacterCallback(callback, range=range(ord('a'), ord('z') + 1)))


def keypressHandler(e):
    global grabbing

    if len(captureCallbacks) > 0:
        cb = captureCallbacks[-1]
        keycode = e.detail
        keysym = keybind.get_keysym(e.detail)

        if not cb(keycode, keysym):
            captureCallbacks.pop()

            if len(captureCallbacks) == 0:
                keybind.ungrab_keyboard()
