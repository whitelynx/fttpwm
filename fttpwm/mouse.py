import logging

import xcb
from xcb.xproto import ButtonMask, ConfigWindow, StackMode

import xpybutil
import xpybutil.event as event
import xpybutil.mousebind as mousebind

from .bind import processBinding
from .keyboard import FilteredHandler
from .utils import convertAttributes, signedToUnsigned16


logger = logging.getLogger("fttpwm.mouse")

captureCallbacks = []


def bindMouse(bindings):
    for buttonString, binding in bindings.iteritems():
        binding = processBinding(binding)
        buttonString = buttonString.replace('+', '-')

        mods, button = mousebind.parse_buttonstring(buttonString)
        if not mousebind.grab_button(xpybutil.root, mods, button):
            logger.error("Couldn't grab mouse button %r!", buttonString)
            return

        logger.debug("Binding mouse button %r. (button=%r, mods=%r)", buttonString, button, mods)

        if binding.onPress is not None:
            logger.debug("Binding ButtonPress event to onPress (%r)", binding.onPress)
            event.connect('ButtonPress', xpybutil.root, FilteredHandler(binding.onPress, button, mods))

        # After the button has been pressed, it will show up in the modifiers.
        mods |= getattr(ButtonMask, '_{}'.format(button))

        if binding.onRelease is not None:
            logger.debug("Binding ButtonRelease event to onRelease (%r)", binding.onRelease)
            event.connect('ButtonRelease', xpybutil.root, FilteredHandler(binding.onRelease, button, mods))

        if binding.onMotion is not None:
            logger.debug("Binding MotionNotify event to onMotion (%r)", binding.onMotion)
            # Motion events always have 0 in event.detail.
            event.connect('MotionNotify', xpybutil.root, FilteredHandler(binding.onMotion, 0, mods))


class MouseDragAction(object):
    CancelDrag = object()

    def __init__(self, onStart=None, onUpdate=None, onFinish=None):
        self.active = False
        self.dragStart = None

        if onStart is not None:
            self.onStartDrag = onStart
        if onUpdate is not None:
            self.onUpdateDrag = onUpdate
        if onFinish is not None:
            self.onFinishDrag = onFinish

    def onPress(self, event):
        if self.onStartDrag(event) is not self.CancelDrag:
            logger.debug("%s: Drag started.", self.__class__.__name__)

            self.active = True
            self.dragStart = event.root_x, event.root_y

    def onRelease(self, event):
        if self.active:
            self.onFinishDrag(event)
            logger.debug("%s: Drag finished.", self.__class__.__name__)

            self.active = False
            self.dragStart = None

    def onMotion(self, event):
        if self.active:
            startX, startY = self.dragStart

            # See how the pointer has moved relative to the root window.
            xDiff = event.root_x - startX
            yDiff = event.root_y - startY

            self.onUpdateDrag(xDiff, yDiff, event)

    def onStartDrag(self, event):
        pass

    def onUpdateDrag(self, xDiff, yDiff, event):
        pass

    def onFinishDrag(self, event):
        pass


class _MoveWindow(MouseDragAction):
    """Move the focused window with the mouse.

    """
    def __init__(self):
        super(_MoveWindow, self).__init__()
        self.window = None
        self._initialGeometry = None
        self.initialGeometryCookie = None

    @property
    def initialGeometry(self):
        if self._initialGeometry is None and self.initialGeometryCookie is not None:
            self._initialGeometry = self.initialGeometryCookie.reply()
            self.initialGeometryCookie = None

        return self._initialGeometry

    def onStartDrag(self, event):
        if event.child != xcb.NONE:
            self.window = event.child
            self.initialGeometryCookie = xpybutil.conn.core.GetGeometry(self.window)

        else:
            return self.CancelDrag

    def onUpdateDrag(self, xDiff, yDiff, event):
        x = self.initialGeometry.x + xDiff
        y = self.initialGeometry.y + yDiff
        xpybutil.conn.core.ConfigureWindow(self.window, *convertAttributes({
                ConfigWindow.X: signedToUnsigned16(x),
                ConfigWindow.Y: signedToUnsigned16(y)
                }))
        xpybutil.conn.flush()

    def onFinishDrag(self, event):
        self.window = None
        self._initialGeometry = None

moveWindow = _MoveWindow()


class _ResizeWindow(_MoveWindow):
    """Resize the focused window with the mouse.

    """
    def onUpdateDrag(self, xDiff, yDiff, event):
        xpybutil.conn.core.ConfigureWindow(self.window, *convertAttributes({
                ConfigWindow.Width: max(1, self.initialGeometry.width + xDiff),
                ConfigWindow.Height: max(1, self.initialGeometry.height + yDiff)
                }))
        xpybutil.conn.flush()

resizeWindow = _ResizeWindow()


def raiseWindow(event):
    """Raise the selected window.

    """
    xpybutil.conn.core.ConfigureWindow(event.child, *convertAttributes({
        ConfigWindow.StackMode: StackMode.Above
        }))
    xpybutil.conn.flush()
