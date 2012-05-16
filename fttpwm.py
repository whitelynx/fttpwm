# Really, really ugly notes on how to start out...

from argparse import Namespace
import logging
import os

import xcb
import xcb.xproto
import xcb.render

import xpybutil
import xpybutil.event as event
#import xpybutil.ewmh as ewmh
import xpybutil.keybind as keybind
import xpybutil.mousebind as mousebind


logger = logging.getLogger("fttpwm")

xConnParams = {
        # By default, xcb will use the DISPLAY and XAUTHORITY environment variables, so you shouldn't need these.
        #'display': ':0.0',
        #'fd': 3,
        #'auth': 'NAME:binary-data',
        }

conn = xcb.connect(**xConnParams)

conn.pref_screen
conn.flush()
conn.wait_for_event()
conn.generate_id()
conn.get_setup()

conn.render = conn(xcb.render.key)

setup = conn.get_setup()
root = setup.roots[0].root
depth = setup.roots[0].root_depth
visual = setup.roots[0].root_visual

window = conn.generate_id()
pid = conn.generate_id()


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


def mark_window():
    captureLetter(do_mark_window)


def goto_window():
    captureLetter(do_goto_window)


captureCallbacks = []


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


settingsFiles = (
        os.path.expanduser("~/.fttpwmrc.py"),
        "/etc/fttpwmrc.py",
        os.path.join(os.path.dirname(__file__), "default_fttpwmrc.py")
        )

for filename in settingsFiles:
    if os.path.exists(filename):
        settingsFile = filename

settings = {}

execfile(settingsFile, globals={}, locals=settings)


# This has to come first so it is called first in the event loop
event.connect('KeyPress', xpybutil.root, keypressHandler)

for key_str, func in settings['keys'].iteritems():
    if not keybind.bind_global_key('KeyPress', key_str, func):
        logger.error('Could not bind %s to %r!', key_str, func)

event.main()


#######################################################################################################################


def find_format(screen):
    for d in screen.depths:
        if d.depth == depth:
            for v in d.visuals:
                if v.visual == visual:
                    return v.format

    raise Exception("Failed to find an appropriate Render pictformat!")


def startup():
    white = setup.roots[0].white_pixel

    conn.core.CreateWindow(
            depth, window, root,
            0, 0, 640, 480, 0,
            xcb.proto.WindowClass.InputOutput,
            visual,
            xcb.proto.CW.BackPixel | xcb.proto.CW.xcb.proto.EventMask,
            [white, xcb.proto.EventMask.ButtonPress | xcb.proto.EventMask.EnterWindow | xcb.proto.EventMask.LeaveWindow | xcb.proto.EventMask.Exposure]
            )

    cookie = conn.render.QueryPictFormats()
    reply = cookie.reply()
    format = find_format(reply.screens[0])

    name = 'X Python Binding Demo'
    conn.core.ChangeProperty(xcb.proto.PropMode.Replace, window, xcb.XA_WM_NAME, xcb.XA_STRING, 8, len(name), name)
    conn.render.CreatePicture(pid, window, format, 0, [])
    conn.core.MapWindow(window)
    conn.flush()


def paint():
    conn.core.ClearArea(False, window, 0, 0, 0, 0)

    for x in xrange(0, 7):
        for y in xrange(0, 5):
            rectangle = ((x + 1) * 24 + x * 64, (y + 1) * 24 + y * 64, 64, 64)
            color = (x * 65535 / 7, y * 65535 / 5, (x * y) * 65535 / 35, 65535)
            conn.render.FillRectangles(xcb.render.PictOp.Src, pid, color, 1, rectangle)

    conn.flush()


def run():
    startup()
    print 'Click in window to exit.'

    while True:
        try:
            event = conn.wait_for_event()
        except xcb.ProtocolException, error:
            print "Protocol error %s received!" % error.__class__.__name__
            break
        except:
            print "Unexpected error received: %s" % error.message
            break

        if isinstance(event, xcb.proto.ExposeEvent):
            paint()
        elif isinstance(event, xcb.proto.EnterNotifyEvent):
            print 'Enter (%d, %d)' % (event.event_x, event.event_y)
        elif isinstance(event, xcb.proto.LeaveNotifyEvent):
            print 'Leave (%d, %d)' % (event.event_x, event.event_y)
        elif isinstance(event, xcb.proto.ButtonPressEvent):
            print 'Button %d down' % event.detail
            break

    conn.disconnect()
