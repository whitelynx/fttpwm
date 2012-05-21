import logging

import xcb
from xcb.xproto import ButtonMask, ConfigWindow, StackMode

import xpybutil
import xpybutil.event as event
import xpybutil.mousebind as mousebind

from .bind import processBinding, FilteredHandler
from .utils import convertAttributes, signedToUnsigned16


logger = logging.getLogger("fttpwm.mouse")

captureCallbacks = []


def bindMouse(bindings, context=xpybutil.root):
    for buttonString, binding in bindings.iteritems():
        binding = processBinding(binding)
        buttonString = buttonString.replace('+', '-')

        mods, button = mousebind.parse_buttonstring(buttonString)
        if not mousebind.grab_button(context, mods, button):
            logger.error("Couldn't grab mouse button %r!", buttonString)
            return

        logger.debug("Binding mouse button %r. (button=%r, mods=%r)", buttonString, button, mods)

        if binding.onPress is not None:
            logger.debug("Binding ButtonPress event to onPress (%r)", binding.onPress)
            event.connect('ButtonPress', context, FilteredHandler(binding.onPress, button, mods))

        # After the button has been pressed, it will show up in the modifiers.
        mods |= getattr(ButtonMask, '_{}'.format(button))

        if hasattr(binding, 'onRelease') and binding.onRelease is not None:
            logger.debug("Binding ButtonRelease event to onRelease (%r)", binding.onRelease)
            event.connect('ButtonRelease', context, FilteredHandler(binding.onRelease, button, mods))

        if hasattr(binding, 'onMotion') and binding.onMotion is not None:
            logger.debug("Binding MotionNotify event to onMotion (%r)", binding.onMotion)
            # Motion events always have 0 in event.detail.
            event.connect('MotionNotify', context, FilteredHandler(binding.onMotion, 0, mods))


class KeyOrButtonAction(object):
    def onPress(self, event):
        pass

    def onRelease(self, event):
        pass


class MouseMoveAction(KeyOrButtonAction):
    def onMotion(self, event):
        pass


class MouseDragAction(MouseMoveAction):
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

        else:
            self.onFinishDrag(0, 0, event, True)

    def onRelease(self, event):
        if self.active:
            # See how the pointer has moved relative to the root window.
            startX, startY = self.dragStart
            xDiff = event.root_x - startX
            yDiff = event.root_y - startY

            self.onFinishDrag(xDiff, yDiff, event, False)
            logger.debug("%s: Drag finished.", self.__class__.__name__)

            self.active = False
            self.dragStart = None

    def onMotion(self, event):
        if self.active:
            # See how the pointer has moved relative to the root window.
            startX, startY = self.dragStart
            xDiff = event.root_x - startX
            yDiff = event.root_y - startY

            if self.onUpdateDrag(xDiff, yDiff, event) is self.CancelDrag:
                self.onFinishDrag(xDiff, yDiff, event, True)

    def onStartDrag(self, event):
        """Override this method in subclasses to do something when a drag starts.

        Return self.CancelDrag to prevent the drag from continuing.

        """
        pass

    def onUpdateDrag(self, xDiff, yDiff, event):
        """Override this method in subclasses to do something when a drag starts.

        Return self.CancelDrag to prevent the drag from continuing.

        """
        pass

    def onFinishDrag(self, xDiff, yDiff, event, canceled):
        """Override this method in subclasses to do something when the drag finishes.

        If canceled == True, this drag was canceled by onStartDrag or onUpdateDrag returning self.CancelDrag.

        """
        pass


class WindowDragAction(MouseDragAction):
    """A drag action that has to do with the window over which the drag started.

    """
    def __init__(self):
        super(WindowDragAction, self).__init__()
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
        """Override this method in subclasses to do something when a drag starts.

        Don't forget to call super(YourClass, self).onStartDrag(event)!

        """
        if event.child != xcb.NONE:
            self.window = event.child
            self.initialGeometryCookie = xpybutil.conn.core.GetGeometry(self.window)
            xpybutil.conn.flush()

        else:
            return self.CancelDrag

    def onUpdateDrag(self, xDiff, yDiff, event):
        """Override this method in subclasses to do something while the drag is happening.

        """
        pass

    def onFinishDrag(self, xDiff, yDiff, event, canceled):
        """Override this method in subclasses to do something when the drag finishes.

        Don't forget to call super(YourClass, self).onFinishDrag(xDiff, yDiff, event, canceled)!

        """
        self.window = None
        self._initialGeometry = None


class _MoveWindow(WindowDragAction):
    """Move the focused window with the mouse.

    """
    def onUpdateDrag(self, xDiff, yDiff, event):
        x = self.initialGeometry.x + xDiff
        y = self.initialGeometry.y + yDiff
        xpybutil.conn.core.ConfigureWindow(self.window, *convertAttributes({
                ConfigWindow.X: signedToUnsigned16(x),
                ConfigWindow.Y: signedToUnsigned16(y)
                }))
        xpybutil.conn.flush()

#FIXME: Should we be using the classes as factories instead of singletons? Is there different state we need to store in
# each binding?
moveWindow = _MoveWindow()


class _ResizeWindow(WindowDragAction):
    """Resize the focused window with the mouse.

    """
    def onUpdateDrag(self, xDiff, yDiff, event):
        xpybutil.conn.core.ConfigureWindow(self.window, *convertAttributes({
                ConfigWindow.Width: max(1, self.initialGeometry.width + xDiff),
                ConfigWindow.Height: max(1, self.initialGeometry.height + yDiff)
                }))
        xpybutil.conn.flush()

resizeWindow = _ResizeWindow()


def _combine(action1, action2):
    if isinstance(action2, type):
        Action2Class = action2
    else:
        Action2Class = action2.__class__

    if issubclass(Action2Class, MouseDragAction):
        class Combined(Action2Class):
            def onStartDrag(self, event):
                action1(event)

                super(Combined, self).onStartDrag(event)

    else:
        assert issubclass(Action2Class, KeyOrButtonAction)

        class Combined(Action2Class):
            def onPress(self, event):
                action1(event)

                super(Combined, self).onPress(event)

    Combined.__name__ = '{}_and_{}'.format(action1.__name__.strip('_'), Action2Class.__name__.strip('_'))
    return Combined()


def _raise(event):
    if event.child != xcb.NONE:
        xpybutil.conn.core.ConfigureWindow(event.child, *convertAttributes({
            ConfigWindow.StackMode: StackMode.Above
            }))
        xpybutil.conn.flush()


def _raiseAnd(Action2):
    return _combine(_raise, Action2)


raiseAndMoveWindow = _raiseAnd(_MoveWindow)

raiseAndResizeWindow = _raiseAnd(_ResizeWindow)


class _RaiseWindow(KeyOrButtonAction):
    """Raise the selected window.

    """
    def onPress(self, event):
        _raise(event)

raiseWindow = _RaiseWindow()
