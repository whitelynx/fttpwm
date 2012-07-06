# -*- coding: utf-8 -*-
from __future__ import unicode_literals
"""FTTPWM: D-Bus client connection

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

NOTE: This implementation ONLY supports UNIX domain sockets currently. This will most likely be extended in the future,
but for now it limits what you can connect to.

"""
from abc import ABCMeta
from binascii import hexlify, unhexlify
from getpass import getuser
from hashlib import sha1
import logging
import os
from os.path import join as joinpath, expanduser
import socket
import urllib


logger = logging.getLogger('fttpwm.dbus.connection')


class Bus(object):
    __metaclass__ = ABCMeta

    def __init__(self):
        self.serverUUID = None

    @property
    def serverGUID(self):
        return self.serverUUID

    def parseAddressOptions(self, optionString):
        options = dict()

        for kvp in optionString.split(','):
            key, value = kvp.split('=')
            options[key] = urllib.unquote(value)

        return options

    def connect(self, address=None):
        if address is None:
            address = self.address

        for addr in address.split(';'):
            transport, options = addr.split(':', 1)

            if transport == 'unix':
                options = self.parseAddressOptions(options)

                try:
                    socketAddress = options['path']
                except KeyError:
                    try:
                        socketAddress = '\0' + options['abstract']
                    except KeyError:
                        continue

                try:
                    self.socket = socket.socket(socket.AF_UNIX)
                    self.socket.connect(socketAddress)
                    self.socket.send('\0')

                    if self.auth_DBUS_COOKIE_SHA1():
                        logger.info("Authentication succeeded.")
                        return

                    else:
                        logger.warn("Authentication failed!")

                except socket.error:
                    continue

                except:
                    logger.exception("Exception encountered while attempting to connect to D-Bus!")
                    continue

            else:
                logger.warn("Unsupported D-Bus connection transport: %r", transport)

        logger.error("Couldn't connect to any D-Bus servers! Giving up.")

    def send(self, data):
        self.socket.send(data)

    def auth_send(self, *data):
        if len(data) > 1:
            data = ' '.join(data) + '\r\n'
        else:
            data = data[0]

        logger.debug("Sending data: %r", data)
        self.send(data)

    def auth_sendData(self, *data):
        data = ' '.join(data)

        self.auth_send('DATA', hexlify(data))

    def recv(self):
        return self.socket.recv(2048)

    def auth_recv(self):
        response = self.recv().split()
        logger.debug("Received response: %r", response)

        if response[0] == 'DATA':
            return unhexlify(response[1]).split()

        return response

    def auth_checkSuccess(self):
        response = self.auth_recv()
        if response[0] == 'OK':
            self.serverUUID = response[1]
            self.auth_send('BEGIN')
            return True
        else:
            logger.debug("Unexpected response to authentication: %r", response)
            return False

    def auth_DBUS_COOKIE_SHA1(self):
        self.auth_send('AUTH', 'DBUS_COOKIE_SHA1', hexlify(getuser()))
        cookieContext, cookieID, serverChallenge = self.auth_recv()

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
        self.auth_sendData('{} {}'.format(clientChallenge, responseHash))

        return self.auth_checkSuccess()

    def auth_ANONYMOUS(self):
        self.auth_send('AUTH', 'ANONYMOUS')

        return self.auth_checkSuccess()


class SessionBus(Bus):
    @property
    def address(self):
        return os.environ['DBUS_SESSION_BUS_ADDRESS']


class SystemBus(Bus):
    @property
    def address(self):
        return os.environ['DBUS_SYSTEM_BUS_ADDRESS']
