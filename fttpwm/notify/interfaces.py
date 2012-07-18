# -*- coding: utf-8 -*-
"""FTTPWM: Desktop notifications client

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from fttpwm import singletons

from fttpwm.dbus.interface import DBusInterface, Method, Signal
from fttpwm.dbus.local import LocalObject
from fttpwm.dbus.remote import RemoteObject
from fttpwm.dbus.proto import types


serverPath = '/org/freedesktop/Notifications'
serverBusID = 'org.freedesktop.Notifications'


### The interface ###
class NotificationsInterface(DBusInterface('org.freedesktop.Notifications')):
    @Method(inSig='', outSig='as', resultFields='capabilities')
    def GetCapabilities(self):
        """Returns an array of strings, each of which describes an optional capability implemented by the server.

        The following capabilities are defined by the spec:

        - "action-icons": Supports using icons instead of text for displaying actions. Using icons for actions must be
            enabled on a per-notification basis using the "action-icons" hint.
        - "actions": The server will provide the specified actions to the user. Even if this cap is missing, actions
            may still be specified by the client, however the server is free to ignore them.
        - "body": Supports body text. Some implementations may only show the summary (for instance, onscreen displays,
            marquee/scrollers)
        - "body-hyperlinks": The server supports hyperlinks in the notifications.
        - "body-images": The server supports images in the notifications.
        - "body-markup": Supports markup in the body text. If marked up text is sent to a server that does not give
            this cap, the markup will show through as regular text so must be stripped clientside.
        - "icon-multi": The server will render an animation of all the frames in a given image array. The client may
            still specify multiple frames even if this cap and/or "icon-static" is missing, however the server is free
            to ignore them and use only the primary frame.
        - "icon-static": Supports display of exactly 1 frame of any given image array. This value is mutually exclusive
            with "icon-multi", it is a protocol error for the server to specify both.
        - "persistence": The server supports persistence of notifications. Notifications will be retained until they
            are acknowledged or removed by the user or recalled by the sender. The presence of this capability allows
            clients to depend on the server to ensure a notification is seen and eliminate the need for the client to
            display a reminding function (such as a status icon) of its own.
        - "sound": The server supports sounds on notifications. If returned, the server must support the "sound-file"
            and "suppress-sound" hints.

        """

    @Method(inSig='', outSig='ssss', resultFields='name vendor version specVersion')
    def GetServerInformation(self):
        """Retrieve the server's name, vendor, and version number.

        """

    @Method(inSig='susssasa{ss}i', outSig='u', resultFields='id')
    def Notify(self, appName, replacesID=0, appIcon='', summary='', body='', actions=[], hints={}, expireTimeout=-1):
        """Send a notification to the notification server.

        """

    @Method(inSig='u', outSig='')
    def CloseNotification(self, id):
        """Causes a notification to be forcefully closed and removed from the user's view. It can be used, for example,
        in the event that what the notification pertains to is no longer relevant, or to cancel a notification with no
        expiration time.

        """

    @Signal(sig='uu')
    def NotificationClosed(id, reason):
        """A notification has timed out, or has been dismissed by the user.

        Possible values for reason:

        1: The notification expired.
        2: The notification was dismissed by the user.
        3: The notification was closed by a call to CloseNotification.
        4: Undefined/reserved reasons.

        """

    @Signal(sig='us')
    def ActionInvoked(id, actionKey):
        """An action has been invoked on a notification.

        This signal is emitted when one of the following occurs:

        - The user performs some global "invoking" action upon a notification. For instance, clicking somewhere on the
            notification itself.
        - The user invokes a specific action as specified in the original Notify request. For example, clicking on an
            action button.

        """


###################################


class NotificationServer(LocalObject):
    def __init__(self, object_path, bus=None):
        if bus is None:
            bus = singletons.dbusSessionBus
        super(NotificationServer, self).__init__(object_path, bus)

    @NotificationsInterface.GetCapabilities
    def GetCapabilities(self):
        """Returns an array of strings, each of which describes an optional capability implemented by the server.

        """

    @NotificationsInterface.GetServerInformation
    def GetServerInformation(self):
        """Retrieve the server's name, vendor, and version number.

        """

    @NotificationsInterface.Notify
    def Notify(self, appName, replacesID, appIcon, summary, body='', actions=[], hints={}, expireTimeout=-1):
        """Send a notification to the notification server.

        """

    @NotificationsInterface.CloseNotification
    def CloseNotification(self, id):
        """Causes a notification to be forcefully closed and removed from the user's view. It can be used, for example,
        in the event that what the notification pertains to is no longer relevant, or to cancel a notification with no
        expiration time.

        """

    @NotificationsInterface.NotificationClosed
    def NotificationClosed(id, reason):
        """A notification has timed out, or has been dismissed by the user.

        """
        # Run just before the signal is actually emitted.

    @NotificationsInterface.ActionInvoked
    def ActionInvoked(id, actionKey):
        """An action has been invoked on a notification.

        """
        # Run just before the signal is actually emitted.


### Creating a remote proxy object ###
class RemoteNotificationServer(RemoteObject):
    notifications = NotificationsInterface()

notifications = RemoteNotificationServer(
        singletons.dbusSessionBus,  # Our connection to the bus
        serverPath,  # The remote object's path
        serverBusID  # The bus name of the connection this remote object lives on
        )


### Calling a method on a remote proxy object ###
appName = 'fttpwm examples'
replacesID = 0
appIcon = ''
summary = "Something happened!"
body = "...and that something is a test."
actions = []
hints = {}
expireTimeout = -1

notifications.Notify(appName, replacesID, appIcon, summary, body, actions, hints, expireTimeout)

# Or, specifying a full type:
notifications.Notify(
        types.String(appName),
        types.UInt32(replacesID),
        types.String(appIcon),
        types.String(summary),
        types.String(body),
        types.ARRAY(types.String)(actions),
        types.DICT(types.String, types.String)(hints),
        types.Int32(expireTimeout)
        )


# If more than one interface on the remote object defines the same method, we need to specify which interface to use:
notifications.notifications.Notify(appName, replacesID, appIcon, summary, body, actions, hints, expireTimeout)

# Alternate way to specify the interface:
notifications.Notify[NotificationsInterface](
        appName, replacesID, appIcon, summary, body, actions, hints, expireTimeout)
