"""FTTPWM: Window layout actions

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import xcb
from xcb.xproto import ConfigWindow, StackMode

import xpybutil

from ..mouse import combine, KeyOrButtonAction, MouseDragAction, WindowDragAction
from ..utils import convertAttributes, signedToUnsigned16
from .. import layout, wm


## Window Action Implementations for Floating Layouts ####
def _onlyFloating(action):
    if isinstance(action, type):
        ActionClass = action
    else:
        ActionClass = action.__class__

    if issubclass(ActionClass, MouseDragAction):
        class OnlyFloating(ActionClass):
            def onStartDrag(self, event):
                if not isinstance(wm.WM.instance.workspaces.currentWorkspace, layout.Floating):
                    return self.CancelDrag

                super(OnlyFloating, self).onStartDrag(event)

    else:
        assert issubclass(ActionClass, KeyOrButtonAction)

        class OnlyFloating(ActionClass):
            def onPress(self, event):
                if not isinstance(wm.WM.instance.workspaces.currentWorkspace, layout.Floating):
                    self.releaseGrabAndReplay(event)
                    return

                super(OnlyFloating, self).onPress(event)

    OnlyFloating.__name__ = ActionClass.__name__.strip('_')
    return OnlyFloating()


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


class _ResizeWindow(WindowDragAction):
    """Resize the focused window with the mouse.

    """
    def onUpdateDrag(self, xDiff, yDiff, event):
        xpybutil.conn.core.ConfigureWindow(self.window, *convertAttributes({
                ConfigWindow.Width: max(1, self.initialGeometry.width + xDiff),
                ConfigWindow.Height: max(1, self.initialGeometry.height + yDiff)
                }))
        xpybutil.conn.flush()


def _raise(event, flush=True):
    if event.child != xcb.NONE:
        xpybutil.conn.core.ConfigureWindow(event.child, *convertAttributes({
                ConfigWindow.StackMode: StackMode.Above
                }))

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
