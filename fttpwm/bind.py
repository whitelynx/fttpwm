from argparse import Namespace
import logging

import xcb

import xpybutil
import xpybutil.event as event
import xpybutil.keybind as keybind
import xpybutil.mousebind as mousebind

from .settings import settings


logger = logging.getLogger("fttpwm.bind")

captureCallbacks = []


def processBinding(binding):
    if isinstance(binding, (tuple, list)):
        return Namespace(
                onPress=binding[0],
                onRelease=binding[1] if len(binding) > 1 else None,
                onMotion=binding[2] if len(binding) > 2 else None
                )
    elif isinstance(binding, dict):
        return Namespace(**binding)
    else:
        return Namespace(onPress=binding)


def bindKeys(bindings):
    for keyString, binding in bindings.iteritems():
        binding = processBinding(binding)

        if binding.onPress is not None:
            if not keybind.bind_global_key('KeyPress', keyString, binding.onPress):
                logger.error("Couldn't bind key press %s to %r!", keyString, binding.onPress)

        if binding.onRelease is not None:
            if not keybind.bind_global_key('KeyRelease', keyString, binding.onRelease):
                logger.error("Couldn't bind key release %s to %r!", keyString, binding.onRelease)


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


def bindConfiguredKeys():
    # This has to come first so it is called first in the event loop
    event.connect('KeyPress', xpybutil.root, keypressHandler)

    for key_str, func in settings['keys'].iteritems():
        if not keybind.bind_global_key('KeyPress', key_str, func):
            logger.error('Could not bind %s to %r!', key_str, func)
