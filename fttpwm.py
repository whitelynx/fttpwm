# Really, really ugly notes on how to start out...

import logging
import os

import xcb
import xcb.xproto
import xcb.render

import xpybutil
import xpybutil.event as event
import xpybutil.ewmh as ewmh
import xpybutil.keybind as keybind


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


dpy.screen().root.grab_key(dpy.keysym_to_keycode(XK.string_to_keysym("F1")), X.Mod1Mask, 1,
        X.GrabModeAsync, X.GrabModeAsync)
dpy.screen().root.grab_button(1, X.Mod1Mask, 1, X.ButtonPressMask|X.ButtonReleaseMask|X.PointerMotionMask,
        X.GrabModeAsync, X.GrabModeAsync, X.NONE, X.NONE)
dpy.screen().root.grab_button(3, X.Mod1Mask, 1, X.ButtonPressMask|X.ButtonReleaseMask|X.PointerMotionMask,
        X.GrabModeAsync, X.GrabModeAsync, X.NONE, X.NONE)


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


def captureLetter(callback):
    captureKeypresses(GetCharacterCallback(callback, range=range(ord('a'), ord('z') + 1)))


def captureKeypresses(callback):
    global captureCallbacks

    GS = xcb.xproto.GrabStatus
    if keybind.grab_keyboard(xpybutil.root).status == GS.Success:
        captureCallbacks.append(callback)


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


settingsFile = os.path.expanduser("~/.fttpwm.py")
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
