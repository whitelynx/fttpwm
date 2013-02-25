"""FTTPWM: Window layout actions

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import logging

import xcb
from xcb.xproto import Circulate, ConfigWindow

import xpybutil

from ..mouse import combine, KeyOrButtonAction, MouseDragAction, WindowDragAction
from ..utils.x import convertAttributes, signedToUnsigned16
from .. import layout
from .. import singletons


logger = logging.getLogger("fttpwm.bindings.layout")

#FIXME: This module needs to be simplified like crazy! We should be able to just bind things with lists of actions
# instead of requiring a separate 'combine' function, and most of these should be less than half the size they
# currently are.


## Window Action Implementations for Floating Layouts ####
def _onlyFloating(action):
    if isinstance(action, type):
        ActionClass = action
    else:
        ActionClass = action.__class__

    if issubclass(ActionClass, MouseDragAction):
        class OnlyFloating(ActionClass):
            def onStartDrag(self, event):
                if not isinstance(singletons.wm.workspaces.current.layout, layout.Floating):
                    return self.CancelDrag

                super(OnlyFloating, self).onStartDrag(event)

    elif issubclass(ActionClass, KeyOrButtonAction):
        class OnlyFloating(ActionClass):
            def onPress(self, event):
                if not isinstance(singletons.wm.workspaces.current.layout, layout.Floating):
                    self.releaseGrabAndReplay(event)
                    return

                super(OnlyFloating, self).onPress(event)

    else:
        assert callable(action)

        class OnlyFloating(KeyOrButtonAction):
            def onPress(self, event):
                if not isinstance(singletons.wm.workspaces.current.layout, layout.Floating):
                    self.releaseGrabAndReplay(event)
                    return

                action(event)

    OnlyFloating.__name__ = ActionClass.__name__.strip('_')
    return OnlyFloating()


class _MoveWindow(WindowDragAction):
    """Move the focused window with the mouse.

    """
    def onUpdateDrag(self, xDiff, yDiff, event):
        #TODO: Support for drawing an outline of the target position instead of constantly moving the window!
        x = self.initialGeometry.x + xDiff
        y = self.initialGeometry.y + yDiff
        xpybutil.conn.core.ConfigureWindow(self.window, *convertAttributes({
                ConfigWindow.X: signedToUnsigned16(x),
                ConfigWindow.Y: signedToUnsigned16(y)
                }))
        xpybutil.conn.flush()


class _ResizeWindow(WindowDragAction):
    """Resize the focused window with the mouse.

    """
    def onUpdateDrag(self, xDiff, yDiff, event):
        #TODO: Support for drawing an outline of the target size instead of constantly resizing the window!
        xpybutil.conn.core.ConfigureWindow(self.window, *convertAttributes({
                ConfigWindow.Width: max(1, self.initialGeometry.width + xDiff),
                ConfigWindow.Height: max(1, self.initialGeometry.height + yDiff)
                }))
        xpybutil.conn.flush()


def tryRaise(window):
    frame = singletons.wm.getFrame(window)
    if frame is None:
        logger.debug("No frame for window %r!", window)
        return False

    frame.raise_(flush=False)

    # For now, auto-focus when raising.
    frame.focus(flush=False)

    return True


def _raise(event, flush=True):
    if event.child == xcb.NONE or not tryRaise(event.child):
        logger.debug("Couldn't raise window for event %r!", event)
        return

    if flush:
        xpybutil.conn.flush()


def _raiseAnd(Action2):
    return combine(_raise, Action2)


class _RaiseWindow(KeyOrButtonAction):
    """Raise the selected window.

    """
    def onPress(self, event):
        self.releaseGrabAndReplay(event, flush=False)

        _raise(event)


def _nextWindow(event, flush=True):
    xpybutil.conn.core.CirculateWindow(Circulate.LowerHighest, singletons.x.root)

    if flush:
        xpybutil.conn.flush()


def _previousWindow(event, flush=True):
    xpybutil.conn.core.CirculateWindow(Circulate.RaiseLowest, singletons.x.root)

    if flush:
        xpybutil.conn.flush()


class Floating(object):
    """Window actions for floating layouts

    """
    #FIXME: Should we be using the classes as factories instead of singletons? Is there different state we need to
    # store in each binding?
    moveWindow = _onlyFloating(_MoveWindow())

    resizeWindow = _onlyFloating(_ResizeWindow())

    raiseAndMoveWindow = _onlyFloating(_raiseAnd(_MoveWindow))

    raiseAndResizeWindow = _onlyFloating(_raiseAnd(_ResizeWindow))

    raiseWindow = _onlyFloating(_RaiseWindow())

    nextWindow = _onlyFloating(_nextWindow)

    previousWindow = _onlyFloating(_previousWindow)


def setLayout(layoutInstance):
    assert isinstance(layoutInstance, layout.BaseLayout)

    def setLayout_(*event):
        ws = singletons.wm.workspaces.current
        logger.debug("Setting workspace %r to layout %r.", ws, layoutInstance)
        ws.setLayout(layoutInstance)

    return setLayout_


def focusNext(*event):
    wm = singletons.wm
    wm.workspaces.current.layout.focusSiblingFrame(wm.focusedWindow, 1)


def focusPrevious(*event):
    wm = singletons.wm
    wm.workspaces.current.layout.focusSiblingFrame(wm.focusedWindow, -1)


def moveNext(*event):
    wm = singletons.wm
    wm.workspaces.current.layout.moveFrame(wm.focusedWindow, 1)


def movePrevious(*event):
    wm = singletons.wm
    wm.workspaces.current.layout.moveFrame(wm.focusedWindow, -1)
