from __future__ import unicode_literals
"""FTTPWM: Application-running actions

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import logging
import shlex
import subprocess


logger = logging.getLogger("fttpwm.bindings.app")


def startSingle(*command, **kwargs):
    """Starts the given command using Popen in response to an event.

    Additional options may be passed to the Popen constructor through `kwargs`.

    """
    if len(command) == 1 and isinstance(command[0], basestring):
        command = shlex.split(command[0])

    kwargs.setdefault('close_fds', True)

    def start_(*event):
        logger.debug("Starting command: %r", command)
        try:
            pid = subprocess.Popen(command, **kwargs).pid
        except:
            logger.exception("Error while starting command %r!", command)
        else:
            logger.debug("Command started; PID: %r", pid)

    return start_


def startParallel(commands, **kwargs):
    """Starts the given set of commands in parallel using Popen in response to an event.

    Additional options may be passed to the Popen constructor through `kwargs`.

    """
    if isinstance(commands, basestring):
        commands = (
                l.split('#', 1)[0].strip()  # Strip comments
                for l in commands.split('\n')  # Split on newlines
                )
        commands = (
                shlex.split(l)
                for l in commands
                if len(l) > 0
                )

    kwargs.setdefault('close_fds', True)

    def start_(*event):
        logger.debug("Starting command set: %r", commands)

        pids = list()
        for command in commands:
            logger.debug("Starting command: %r", command)
            try:
                pids.append(subprocess.Popen(command, **kwargs).pid)
            except:
                logger.exception("Error while starting command %r!", command)
                pids.append(None)

        logger.debug("Command set started; PIDs: %r", pids)

    return start_


def startSerial(commands, **kwargs):
    """Starts the given sequence of commands in serial using Popen in response to an event.

    Additional options may be passed to the Popen constructor through `kwargs`.

    """
    if isinstance(commands, basestring):
        commands = (
                l.split('#', 1)[0].strip()  # Strip comments
                for l in commands.split('\n')  # Split on newlines
                )
        commands = (
                shlex.split(l)
                for l in commands
                if len(l) > 0
                )

    kwargs.setdefault('close_fds', True)

    def start_(*event):
        logger.debug("Starting command sequence: %r", commands)

        #FIXME: This is wrong! It should be spawning up a new process using multiprocessing or something, and then
        # running all the commands in order in that process.
        for command in commands:
            logger.debug("Running command: %r", command)
            try:
                subprocess.check_call(command, **kwargs)
            except:
                logger.exception("Error while starting command %r!", command)

    return start_
