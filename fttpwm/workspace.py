# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: Main application

Copyright (c) 2012-2013 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import logging
import weakref

import xcb

import xpybutil.ewmh as ewmh

from . import singletons
from .settings import settings
from .signals import Signal
from .signaled import SignaledList, SignaledDict
from .layout.simpletile import Rows
from .utils.history import HistoryStack


logger = logging.getLogger("fttpwm.workspace")

settings.setDefaults(
        workspaces=[
            '1:alpha',
            '2:beta',
            '3:gamma',
            '4:delta',
            '5:pi',
            '6:omega',
            '7:phlange',
            '8:dromedary',
            '9:°±²ÛÝÜßÞÛ²±°',
            '0:eü=-1; n=ãi',
            '[:¢Ã¿ªØ',
            ']:äë¡áÀ£ ïüDîÚê3àr',
            #'àáçëãê¯Ù§',
            #'û©ýðñ«ü¡',
            #'õõõõõõõõõõõõõõõõõõ',
            #'¨ª¦¥¤£¢³ºÄÍ¿¸·»ÚÕÖÉÙ¾½¼ÀÔÓÈÃÆÇÌ´µ¶¹ÂÒÑËÁÏÐÊÅØ×Î­úöìíøïõéäîòõù®¬§àáçëãê¯',
            #' ¡¢£¤¥¦§¨©ª«¬­®¯°±²³´µ¶·¸¹º»¼½¾¿ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõö÷øùúûüýþÿ',
            ],
        initialWorkspace=0,
        defaultLayout=Rows(),
        focusNewWindows=False,
        )


class WorkspaceManager(object):
    def __init__(self):
        self.workspaces = SignaledList()
        self.workspacesByName = SignaledDict()
        self.currentChanged = Signal()
        self._currentWorkspaceNum = None

        self.baseWorkAreaUpdated = Signal()
        self.baseWorkAreaUpdated.connect(self.updateWorkAreaHint)
        self.baseWorkAreaUpdated.connect(self.arrangeGlobalDocks)

        singletons.wm.strutsLeft.updated.connect(self.baseWorkAreaUpdated)
        singletons.wm.strutsRight.updated.connect(self.baseWorkAreaUpdated)
        singletons.wm.strutsTop.updated.connect(self.baseWorkAreaUpdated)
        singletons.wm.strutsBottom.updated.connect(self.baseWorkAreaUpdated)

        self.createConfiguredWorkspaces()
        self.setEWMHProps()

        self.currentIndex = min(settings.initialWorkspace, len(self.workspaces) - 1)
        self.current.show()

    def createConfiguredWorkspaces(self):
        del self.workspaces[:]
        self.workspacesByName.clear()

        for index, name in enumerate(settings.workspaces):
            self.createWorkspace(name, index)

    def createWorkspace(self, name, index=None):
        ws = Workspace(self, index, name)
        ws.workAreaUpdated.connect(self.updateWorkAreaHint)
        self.workspacesByName[name] = ws

        if index is not None:
            self.workspaces.insert(index, ws)
        else:
            self.workspaces.append(ws)

    def placeOnWorkspace(self, frame):
        logger.debug("placeOnWorkspace: Placing %r", frame)

        # Pay attention to the _NET_WM_DESKTOP value if initially set by the client, and try to put the window on that
        # workspace. The workspace will then set _NET_WM_DESKTOP to its index.
        workspaceNum = ewmh.get_wm_desktop(frame.clientWindowID)
        if workspaceNum is None or workspaceNum >= len(self.workspaces):
            workspaceNum = self.currentIndex

        self.workspaces[workspaceNum].addWindow(frame)

    def removeWindow(self, frame):
        logger.debug("removeWindow: Removing %r", frame)

        for ws in self.workspaces:
            if frame.clientWindowID in ws.windows:
                logger.debug("removeWindow: Found %r in workspace %r.", frame, ws.index)
                del ws.windows[frame.clientWindowID]

    def setEWMHProps(self):
        ewmh.set_desktop_names(ws.name.encode('utf8') for ws in self.workspaces)
        ewmh.set_number_of_desktops(len(self.workspaces))
        ewmh.set_desktop_geometry(singletons.x.screenWidth, singletons.x.screenHeight)

        # We don't support large desktops, so our viewport is always at 0, 0.
        ewmh.set_desktop_viewport([{'x': 0, 'y': 0}] * len(self.workspaces))

        self.updateWorkAreaHint()

    def updateWorkAreaHint(self):
        ewmh.set_workarea(ws.innerGeometry for ws in self.workspaces)

    @property
    def globalWorkArea(self):
        return {'x': self.globalWorkAreaX, 'y': self.globalWorkAreaY,
                'width': self.globalWorkAreaWidth, 'height': self.globalWorkAreaHeight}

    @property
    def globalWorkAreaX(self):
        return singletons.wm.strutsLeftSize

    @property
    def globalWorkAreaY(self):
        return singletons.wm.strutsTopSize

    @property
    def globalWorkAreaWidth(self):
        return singletons.x.screenWidth - singletons.wm.strutsLeftSize - singletons.wm.strutsRightSize

    @property
    def globalWorkAreaHeight(self):
        return singletons.x.screenHeight - singletons.wm.strutsTopSize - singletons.wm.strutsBottomSize

    def arrangeGlobalDocks(self):
        #TODO: Rearrange any global (non-workspace-specific / "pinned") dock windows as needed!
        pass

    @property
    def currentIndex(self):
        return self._currentWorkspaceNum

    @currentIndex.setter
    def currentIndex(self, value):
        if self._currentWorkspaceNum == value:
            # Skip update if we're already on the requested workspace.
            return

        old = self.current
        if old:
            old.hide()

        self._currentWorkspaceNum = value

        self.current.show()
        ewmh.set_current_desktop(value)
        self.currentChanged()

    @property
    def current(self):
        try:
            return self.workspaces[self.currentIndex]
        except (TypeError, IndexError):
            return None

    @current.setter
    def current(self, workspace):
        self.currentIndex = workspace.index

    @property
    def beforeCurrent(self):
        return self.workspaces[:self.currentIndex]

    @property
    def afterCurrent(self):
        return self.workspaces[self.currentIndex + 1:]

    @property
    def namesBeforeCurrent(self):
        return [ws.name for ws in self.beforeCurrent]

    @property
    def namesAfterCurrent(self):
        return [ws.name for ws in self.afterCurrent]

    def switchTo(self, workspace):
        if isinstance(workspace, basestring):
            workspace = self.workspacesByName[workspace]
        else:
            workspace = self.workspaces[workspace]

        self.current = workspace


class Workspace(object):
    def __init__(self, manager, index, name):
        self.manager = manager
        self.name = name

        self.windows = SignaledDict()
        self.windows.updated.connect(self.arrangeWindows)
        self._focusedWindow = None
        self.focusHistory = HistoryStack()

        self.focusedWindowClosed = Signal()
        self.focusedWindowClosed.connect(self.onFocusedWindowClosed)

        self.indexUpdated = Signal()
        self._index = None
        self.index = index
        manager.workspaces.updated.connect(self.updateIndex)

        self._visible = False
        self.visibilityChanged = Signal()

        self.layout = settings.defaultLayout

        # Start with no local (workspace-specific) struts.
        self.localStrutsLeft, self.localStrutsRight = 0, 0
        self.localStrutsTop, self.localStrutsBottom = 0, 0

        self.workAreaUpdated = Signal()
        self.workAreaUpdated.connect(self.arrangeLocalDocks)
        self.workAreaUpdated.connect(self.arrangeWindows)

        # We don't want to fire workAreaUpdated here; that would generate duplicate calls to manager.updateWorkAreaHint
        manager.baseWorkAreaUpdated.connect(self.arrangeLocalDocks)
        manager.baseWorkAreaUpdated.connect(self.arrangeWindows)

    @property
    def focusedWindow(self):
        if self._focusedWindow is not None:
            return self._focusedWindow()

    @focusedWindow.setter
    def focusedWindow(self, frame):
        previous = self.focusedWindow

        if self.focusedWindow is not None:
            # Disconnect from the previous window's closed signal.
            self.focusedWindow.closed.disconnect(self.focusedWindowClosed)

        if isinstance(frame, weakref.ReferenceType) or frame is None:
            self._focusedWindow = frame
        else:
            self._focusedWindow = weakref.ref(frame)

        if self.focusedWindow is None:
            logger.info("Focused window set to None; focusing next most recently-focused window when idle.")
            singletons.eventloop.callWhenIdle(self.focusMostRecent)

        else:
            # Connect to this window's closed signal.
            self.focusedWindow.closed.connect(self.focusedWindowClosed)

            # Add this window to the focus history.
            self.focusHistory.add(self.focusedWindow)

        self.layout.onFocusChanged(previous, frame)

    def onFocusedWindowClosed(self):
        self.focusedWindow = None

    @staticmethod
    def sortByAddedTime(frame):
        return frame.addedToWorkspace

    def focusMostRecent(self):
        frame = None
        for focused in reversed(list(self.focusHistory)):
            if focused.valid:
                frame = focused
                logger.debug("focusMostRecent: Focusing most recently-focused frame. (%r)", frame)
                break

            else:
                logger.debug("focusMostRecent: Removing invalid frame %r from focus history.", focused)
                self.focusHistory.discard(focused)

        if not frame:
            validFrames = self.validFrames
            if validFrames:
                logger.debug("focusMostRecent: No valid frames in focus history; focusing first frame on workspace.")

                # Get the most recently-added valid frame on this workspace.
                frame = (f for f in sorted(validFrames, key=self.sortByAddedTime)).next()

            else:
                logger.info("focusMostRecent: No valid frames on workspace.")
                return

        if frame:
            logger.info("focusMostRecent: Focusing frame: %r", frame)
            frame.focus()

        else:
            logger.warn("focusMostRecent: No valid windows found.")

    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, value):
        self._visible = value
        self.visibilityChanged()

    @property
    def index(self):
        return self._index

    @index.setter
    def index(self, index):
        if self._index != index:
            if hasattr(self, 'logger'):
                self.logger.debug("index: %r => %r", self._index, index)

            self._index = index
            self.logger = logging.getLogger("fttpwm.workspace.Workspace.{}(name:{})".format(index, self.name))

            # Update each window's _NET_WM_DESKTOP property.
            for clientWindowID in self.windows:
                ewmh.set_wm_desktop(clientWindowID, index)

            self.indexUpdated()

    def updateIndex(self):
        self.index = self.manager.workspaces.index(self)

    @property
    def validFrames(self):
        valid = []
        for frame in self.windows.values():
            if not frame.valid:
                logger.debug("validFrames: Removing invalid frame %r from window list.", frame)
                self.windows.discard(frame)

            else:
                valid.append(frame)

        return valid

    @property
    def hasViewableFrames(self):
        return any(
                frame.viewable
                for frame in self.validFrames
                )

    @property
    def viewableFrames(self):
        return [
                frame
                for frame in self.validFrames
                if frame.viewable
                ]

    @property
    def innerGeometry(self):
        return {'x': self.innerX, 'y': self.innerY,
                'width': self.innerWidth, 'height': self.innerHeight}

    @property
    def innerX(self):
        return self.manager.globalWorkAreaX + self.localStrutsLeft

    @property
    def innerY(self):
        return self.manager.globalWorkAreaY + self.localStrutsTop

    @property
    def innerWidth(self):
        return self.manager.globalWorkAreaWidth - self.localStrutsLeft - self.localStrutsRight

    @property
    def innerHeight(self):
        return self.manager.globalWorkAreaHeight - self.localStrutsTop - self.localStrutsBottom

    def arrangeLocalDocks(self):
        #TODO: Rearrange any local (workspace-specific) dock windows as needed!
        pass

    def setLayout(self, layout):
        self.layout = layout
        self.arrangeWindows()

    def arrangeWindows(self, *source):
        if not self.hasViewableFrames:
            return

        self.layout.arrange(self)

    def show(self):
        self.logger.debug("show: Showing.")

        ewmh.set_current_desktop(self.index)
        self.visible = True
        self.arrangeWindows()

    def hide(self):
        self.logger.debug("hide: Hiding.")

        self.visible = False

    def addWindow(self, frame):
        if frame.clientWindowID in self.windows:
            return

        self.logger.debug("addWindow: Adding window: %s", frame)

        frame.workspace = self

        # Add to our collection of windows; this will trigger arrangeWindows.
        self.windows[frame.clientWindowID] = frame

        # Set the window's _NET_WM_DESKTOP property.
        ewmh.set_wm_desktop(frame.clientWindowID, self.index)

        frame.requestShow.connect(self.arrangeWindows)

        if self.focusedWindow is None or settings.focusNewWindows:
            frame.focus()

    def removeWindow(self, frame):
        self.logger.debug("removeWindow: Removing window: %s", frame)

        if frame.workspace == self:
            frame.workspace = None

        try:
            frame.requestShow.disconnect(self.arrangeWindows)
        except KeyError:
            pass

        # Remove from our collection of windows; this will trigger arrangeWindows.
        if frame.clientWindowID != xcb.NONE:
            del self.windows[frame.clientWindowID]

        else:
            logger.warn("frame.clientWindowID == xcb.NONE!")
            for k in self.windows.keys():
                if self.windows[k] == frame:
                    del self.windows[k]

        # Remove from the focus history.
        del self.focusHistory[frame]
