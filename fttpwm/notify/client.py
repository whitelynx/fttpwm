# -*- coding: utf-8 -*-
"""FTTPWM: Desktop notifications client

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from ..dbus.interfaces.introspectable import Introspectable as IntrospectableInterface
from ..dbus.remote import RemoteObject
from ..signals import Signal
from ..utils import loggerFor

from .interfaces import serverPath, serverBusID, NotificationsInterface


class Server(RemoteObject):
    ## DBus interfaces
    notifications = NotificationsInterface
    introspectable = IntrospectableInterface

    def __init__(self, bus=None):
        super(Server, self).__init__(serverPath, destination=serverBusID, bus=bus)

        self.logger = loggerFor(self)

        self.capabilities = None
        self.name = None
        self.vendor = None
        self.version = None
        self.spec_version = None
        self.infoRetrieved = Signal()

    def getCapabilities(self):
        cb = self.GetCapabilities()
        cb.onReturn = self._onGetCapabilitiesReturn

    def _onGetCapabilitiesReturn(self, response):
        self.logger.info("Got capabilities from notification daemon: %r.", response.body)

        self.capabilities = response.body[0]

    def getServerInformation(self):
        cb = self.GetServerInformation()
        cb.onReturn = self._onServerInformationReturn

    def _onServerInformationReturn(self, response):
        self.logger.info("Got capabilities from notification daemon: %r.", response.body)

        self.name, self.vendor, self.version, self.spec_version = response.body


class Notification(RemoteObject):
    ## DBus interfaces
    notifications = NotificationsInterface
    introspectable = IntrospectableInterface

    _notificationsByBusAndID = dict()

    @classmethod
    def setupSignalHandlers(cls, bus):
        cls.logger = loggerFor(cls)

        if bus not in cls._notificationsByBusAndID:
            cls._notificationsByBusAndID[bus] = dict()

            def handleNotificationsSignal(message):
                notificationsByID = cls._notificationsByBusAndID[bus]
                notificationID = message.body[0]
                handlerName = 'on{}'.format(message.header.member)

                try:
                    getattr(notificationsByID[notificationID], handlerName)(message.body[1:])
                except:
                    cls.logger.exception("Exception encountered calling handler for %r signal on notification %r!",
                            message.header.member, notificationID)

            bus.listenForSignal(interface='org.freedesktop.Notifications', handler=handleNotificationsSignal)

    def __init__(self, appName, body, summary="", appIcon="", actions=[], hints={}, expirationMS=-1, bus=None):
        super(Notification, self).__init__(serverPath, destination=serverBusID, bus=bus)

        self.setupSignalHandlers(self.dbus_bus)

        self.appName = appName
        self._notificationID = 0  # we start with 0 so the server will assign it an ID
        self.appIcon = appIcon
        self.summary = summary
        self.body = body
        self.actions = actions
        self.hints = hints
        self.expirationMS = expirationMS

    @property
    def notificationID(self):
        return self._notificationID

    @notificationID.setter
    def notificationID(self, value):
        if self._notificationID != 0:
            del self._notificationsByBusAndID[self.dbus_bus][self._notificationID]

        self._notificationID = value

        if value != 0:
            self._notificationsByBusAndID[self.dbus_bus][value] = self

    def show(self, onReturn=lambda response: None):
        if self.notificationID != 0:
            self.logger.info("Updating notification message %r: app=%r; summary=%r; body=%r",
                    self.notificationID, self.appName, self.summary, self.body)
        else:
            self.logger.info("Showing notification message for app %r with summary %r: %r.",
                    self.appName, self.summary, self.body)

        def handleReturn(response):
            self.onNotifyReturn(response)
            onReturn(response)

        cb = self.Notify(
                self.appName,
                self.notificationID,  # spec calls this "replaces_id"
                self.appIcon,
                self.summary,
                self.body,
                self.actions,
                self.hints,
                self.expirationMS
                )
        cb.onReturn = handleReturn

    def onNotifyReturn(self, response):
        global notificationID, notificationCount

        if self.notificationID == 0:
            self.logger.info("Got notification ID %r from notification daemon.", response.body[0])
            self.notificationID = response.body[0]

        elif self.notificationID != response.body[0]:
            self.logger.warn("Got notification ID %r from notification daemon, but we have the ID %r! Overwriting.",
                    response.body[0], self.notificationID)
            self.notificationID = response.body[0]

    def close(self):
        self.logger.info("Closing notification message %r.", self.notificationID)

        cb = self.CloseNotification(
                self.notificationID
                )
        cb.onReturn = self.onReturn

    def onNotificationClosed(self, reason):
        '''A completed notification is one that has timed out, or has been dismissed by the user. [sic]

        reason - The reason the notification was closed.
            1 - The notification expired.
            2 - The notification was dismissed by the user.
            3 - The notification was closed by a call to CloseNotification.
            4 - Undefined/reserved reasons.

        '''
        self.logger.debug("The notification was closed; reason: %r", reason)

    def onActionInvoked(self, actionKey):
        '''This signal is emitted when one of the following occurs:
        - The user performs some global "invoking" action upon a notification. For instance, clicking somewhere on the
        notification itself.
        - The user invokes a specific action as specified in the original Notify request. For example, clicking on an
        action button.

        action_key - The key of the action invoked. These match the keys sent over in the list of actions.

        '''
        self.logger.info("The user invoked an action: %r", actionKey)
