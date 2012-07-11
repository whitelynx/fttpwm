# -*- cod-ing: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: D-Bus SASL authentication

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

When I wrote this, I didn't see the note in the spec that this is actually a SASL profile. It may make sense to find a
generalized SASL library for Python and use it instead of this code, though if at all possible it should be pure Python
(not a wrapper for a C/C++ library) to cut down on the number of binary dependencies needed.

"""
from abc import ABCMeta, abstractmethod, abstractproperty
from binascii import hexlify, unhexlify
from getpass import getuser
from hashlib import sha1
import os
from os.path import join as joinpath, expanduser

from ..utils import loggerFor


class Authenticator(object):
    __metaclass__ = ABCMeta

    ## Abstract Members ##

    name = abstractproperty()

    @abstractmethod
    def authenticate(self):
        pass

    ## Implementation ##

    def __init__(self, bus):
        self.logger = loggerFor(self)

        self.bus = bus

    def send(self, *data):
        if len(data) > 1:
            data = ' '.join(data) + '\r\n'
        else:
            data = data[0]

        self.logger.debug("Sending data: %r", data)
        self.bus.send(data)

    def sendData(self, *data):
        data = ' '.join(data)

        self.send('DATA', hexlify(data))

    def recv(self):
        response = self.bus.recv().split()
        self.logger.debug("Received response: %r", response)

        if response[0] == 'DATA':
            return unhexlify(response[1]).split()

        return response

    def checkSuccess(self):
        response = self.recv()
        if response[0] == 'OK':
            self.bus.serverUUID = response[1]
            self.logger.info("Authentication succeeded; beginning session.")
            self.send('BEGIN\r\n')
            return True

        elif response[0] == 'REJECTED':
            self.logger.info("Authentication failed! Supported mechanisms: %s", ' '.join(response[1:]))
            self.bus.reportedAuthMechanisms = response[1:]
            return False

        else:
            self.logger.warn("Unexpected response to authentication: %r", response)
            return False


class CookieSHA1Auth(Authenticator):
    name = 'DBUS_COOKIE_SHA1'

    def authenticate(self):
        self.send('AUTH', 'DBUS_COOKIE_SHA1', hexlify(getuser()))
        cookieContext, cookieID, serverChallenge = self.recv()

        cookiePath = joinpath(expanduser('~/.dbus-keyrings'), cookieContext)
        cookieFile = open(cookiePath, 'r')
        cookie = None
        try:
            for line in cookieFile:
                if line.strip():
                    id, created, cookie = line.split()

                    if id == cookieID:
                        break
        finally:
            cookieFile.close()

        clientChallenge = hexlify(os.urandom(24))
        responseHash = sha1('{}:{}:{}'.format(serverChallenge, clientChallenge, cookie)).hexdigest()
        self.sendData('{} {}'.format(clientChallenge, responseHash))

        return self.checkSuccess()


class AnonymousAuth(Authenticator):
    name = 'ANONYMOUS'

    def authenticate(self):
        self.send('AUTH', 'ANONYMOUS')

        return self.checkSuccess()
