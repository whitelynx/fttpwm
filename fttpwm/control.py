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
    def __init__(self):
        self.local = {
                '__name__': '__console__',
                '__doc__': None,
                '_stdoutput': self,
                }
        self.local.update(singletons.__dict__)

        code.InteractiveInterpreter.__init__(self, self.local)

    def setClientAddr(self, stream, clientAddr):
        self.zmqStream = stream
        self.clientAddr = clientAddr

    def write(self, data):
        self.zmqStream.send_multipart([self.clientAddr, data])

    def displayhook(self, value):
        self.write(repr(value) + '\n')

    def runsource(self, *args):
        sys.displayhook = self.displayhook
        sys.stdout = self
        sys.stderr = self
        code.InteractiveInterpreter.runsource(self, *args)
        sys.displayhook = sys.__displayhook__
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__


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

        #FIXME: Figure out how to clean up interpreters when disconnects happen! (maybe heartbeats and timeouts)
        self.sessions = collections.defaultdict(RemoteInterpreter)

        self.stream = ZMQStream(self.socket)
        self.stream.on_recv(self.execute)

    def execute(self, msg):
        if len(msg) == 3 and msg[1] == 'END':
            # Simply echo the END message back so the client knows it's received all its responses.
            response = msg

        elif len(msg) == 2:
            clientAddr, command = msg

            logger.info("Got remote command from client %r, blindly executing: %r",
                    binascii.hexlify(clientAddr), command)
            try:
                session = self.sessions[clientAddr]
                session.setClientAddr(self.stream, clientAddr)
                session.runsource(command, '<remote>')
                return
            except:
                response = [clientAddr, traceback.format_exc()]

        else:
            clientAddr = msg[0]

            response = [clientAddr, "Invalid request!"]

        self.stream.send_multipart(response)


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
        stream.send("dir(wm)", callback=lambda *a: logger.debug("Stream 1 finished sending message; %r", a))

    #  Do 5 requests on stream 2
    for request in range(0, 5):
        stream2.send("dir(x)", callback=lambda *a: logger.debug("Stream 2 finished sending message; %r", a))

    io_loop.start()
