import argparse
import logging
import os
import sys
import uuid

import zmq
import zmq.eventloop.ioloop
from zmq.eventloop.zmqstream import ZMQStream


logger = logging.getLogger("fttpwm.remote")


def main():
    logging.basicConfig()

    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('commands', metavar='COMMAND', nargs='+',
                       help="a command to run in the fttpwm instance's process")

    args = parser.parse_args()

    io_loop = zmq.eventloop.ioloop.IOLoop.instance()
    context = zmq.Context()
    endMessage = ['END', uuid.uuid1().bytes]

    def handleReply(stream, msg):
        if msg == endMessage:
            io_loop.stop()

        else:
            logger.debug("Stream %r received reply %r", stream, msg)
            sys.stdout.write(msg[0])

    socket = context.socket(zmq.DEALER)
    socket.connect(os.environ['FTTPWM_IPC_ADDR'])

    stream = ZMQStream(socket, io_loop)
    stream.on_recv_stream(handleReply)

    for command in args.commands:
        stream.send_multipart(['COMMAND', command])

    stream.send_multipart(endMessage)

    io_loop.start()


if __name__ == "__main__":
    main()
