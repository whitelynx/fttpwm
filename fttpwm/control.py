"""Remote control server component

"""
import binascii
import code
import collections
import logging
import os
import sys
import traceback

import zmq
from zmq.eventloop.zmqstream import ZMQStream

try:
    from . import singletons
except ValueError:
    pass


logger = logging.getLogger("fttpwm.control")


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


class RemoteControlServer(object):
    def __init__(self):
        context = zmq.Context.instance()

        self.socket = context.socket(zmq.ROUTER)
        port = self.socket.bind_to_random_port("tcp://127.0.0.1")

        logger.info("Remote control server listening on port %s.", port)
        os.environ['FTTPWM_REMOTE_PORT'] = str(port)

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
