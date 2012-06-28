"""Remote control server component

"""
from argparse import Namespace
from string import Template
from os.path import abspath, expanduser
import binascii
import code
import collections
import logging
import os
import re
import sys
import traceback

import zmq
from zmq.eventloop.zmqstream import ZMQStream

try:
    from . import singletons
    from .settings import settings
    from .xdg import basedir
except ValueError:
    pass


logger = logging.getLogger("fttpwm.control")

settings.setDefaults(
        #controlAddress="tcp://127.0.0.1",
        controlAddress=Template("ipc://$XDG_RUNTIME_DIR/fttpwm-$DISPLAY.ipc"),
        )


class RemoteInterpreter(code.InteractiveInterpreter):
    def __init__(self, manager, clientAddr):
        self.manager = manager
        self.zmqStream = manager.stream
        self.clientAddr = clientAddr

        self.local = {
                '__name__': '__console__',
                '__doc__': None,
                }
        self.local.update(singletons.__dict__)

        code.InteractiveInterpreter.__init__(self, self.local)

    def write(self, data):
        self.zmqStream.send_multipart([self.clientAddr, data])

    def displayhook(self, value):
        self.write(repr(value) + '\n')

    def runsource(self, *args):
        sys.displayhook, sys.stdout, sys.stderr = self.displayhook, self, self
        code.InteractiveInterpreter.runsource(self, *args)
        sys.displayhook, sys.stdout, sys.stderr = sys.__displayhook__, sys.__stdout__, sys.__stderr__


class RemoteSessionManager(dict):
    def __init__(self, stream):
        self.sessions = dict()
        self.sessionTimeouts = dict()

        self.stream = stream

    def __getitem__(self, clientAddr):
        if clientAddr not in self.sessions:
            self.sessions[clientAddr] = RemoteInterpreter(self, clientAddr)

        return self.sessions[clientAddr]


addrPattern = re.compile(r'(?P<protocol>\w+)://(?P<endpoint>.*)')
tcpEndpointPattern = re.compile(r'(?P<interface>[^:]+)(?::(?P<port>\d+))?')
pgmEndpointPattern = re.compile(r'(?P<interface>[^;]+);(?P<multicast_addr>[^:]+)(?::(?P<port>\d+))?')


def parseAddr(address):
    match = addrPattern.match(address)

    if not match:
        logger.warn("Invalid address: %r", address)
        return

    groups = match.groupdict()

    if groups['protocol'] == 'tcp':
        match = tcpEndpointPattern.match(address)
        if match:
            groups.update(match.groupdict())
        else:
            logger.warn("Invalid TCP address: %r", address)

    elif groups['protocol'] in ('pgm', 'epgm'):
        match = pgmEndpointPattern.match(address)
        if match:
            groups.update(match.groupdict())
        else:
            logger.warn("Invalid PGM address: %r", address)

    return Namespace(**groups)


def shouldHavePort(protocol):
    return protocol in ('tcp', 'pgm', 'epgm')


class RemoteControlServer(object):
    def __init__(self):
        context = zmq.Context.instance()

        address = settings.controlAddress
        if isinstance(address, Template):
            environ = dict(os.environ.iteritems())
            environ['XDG_RUNTIME_DIR'] = basedir.runtimeDir

            address = address.substitute(**environ)

        self.socket = context.socket(zmq.ROUTER)

        parsed = parseAddr(address)

        if parsed.protocol == 'ipc':
            address = 'ipc://{}'.format(abspath(expanduser(parsed.endpoint)))

        if shouldHavePort(parsed.protocol) and parsed.port is None:
            port = self.socket.bind_to_random_port(address)
            address = '{}:{}'.format(address, port)

        else:
            self.socket.bind(address)

        logger.info("Remote control server listening on %s.", address)
        os.environ['FTTPWM_IPC_ADDR'] = address

        self.stream = ZMQStream(self.socket)
        self.stream.on_recv(self.messageReceived)

        #FIXME: Figure out how to clean up interpreters when disconnects happen! (maybe heartbeats and timeouts)
        self.sessions = RemoteSessionManager(self.stream)

    def handleMessage(self, msg):
        if len(msg) < 2:
            raise ValueError("No opcode specified!")

        clientAddr, opcode = msg[:2]
        payload = msg[2:]
        argc = len(payload)

        if opcode == 'PING':
            return ['PONG']

        elif opcode == 'END':
            # Simply echo the END message back so the client knows it's received all its responses.
            return msg[1:]

        elif opcode == 'COMMAND':
            if argc > 1:
                raise ValueError("Too many arguments for opcode 'COMMAND'! (takes 1 argument; %d given)" % (argc, ))
            elif argc < 1:
                raise ValueError("Not enough arguments for opcode 'COMMAND'! (takes 1 argument; %d given)" % (argc, ))

            logger.info("Got remote command from client %s, blindly executing: %r",
                    binascii.hexlify(clientAddr), payload[0])

            try:
                session = self.sessions[clientAddr]
                session.runsource(payload[0], '<remote>')
                return

            except:
                return [traceback.format_exc()]

        return ["Invalid request!"]

    def messageReceived(self, msg):
        clientAddr = msg[0]
        logger.debug("Got message from %s: %r", binascii.hexlify(clientAddr), msg[1:])

        try:
            response = self.handleMessage(msg)
        except Exception as ex:
            logger.warn("Exception encountered while running command for client %r!",
                    binascii.hexlify(clientAddr), exc_info=True)
            response = ['ERROR', str(ex)]

        if response:
            logger.debug("Sending response for command from client %s: %r",
                    binascii.hexlify(clientAddr), response)
            self.stream.send_multipart([clientAddr] + response)
        else:
            logger.debug("Finished running command from client %s; no response to send.",
                    binascii.hexlify(clientAddr))


if __name__ == '__main__':
    import zmq.eventloop.ioloop

    logging.basicConfig(level=logging.NOTSET)

    io_loop = zmq.eventloop.ioloop.IOLoop.instance()
    context = zmq.Context()

    received = 0

    def showReply(stream, msg):
        global received
        logger.debug("Stream %r received reply %r", stream, msg)

        received += 1
        if received >= 15:
            io_loop.stop()

    socket = context.socket(zmq.DEALER)
    socket.connect("tcp://localhost:{}".format(os.environ['FTTPWM_REMOTE_PORT']))
    stream = ZMQStream(socket, io_loop)
    stream.on_recv_stream(showReply)

    socket2 = context.socket(zmq.DEALER)
    socket2.connect("tcp://localhost:{}".format(os.environ['FTTPWM_REMOTE_PORT']))
    stream2 = ZMQStream(socket2, io_loop)
    stream2.on_recv_stream(showReply)

    #  Do 10 requests on stream 1
    for request in range(0, 10):
        stream.send_multipart(
                ['COMMAND', "dir(wm)"],
                callback=lambda *a: logger.debug("Stream 1 finished sending message; %r", a)
                )

    #  Do 5 requests on stream 2
    for request in range(0, 5):
        stream2.send_multipart(
                ['COMMAND', "dir(x)"],
                callback=lambda *a: logger.debug("Stream 2 finished sending message; %r", a)
                )

    io_loop.start()
