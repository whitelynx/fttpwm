from __future__ import unicode_literals
"""FTTPWM: Application-running actions

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from collections import defaultdict
import logging
import multiprocessing
import os
import shlex
from string import Template
import subprocess


logger = logging.getLogger("fttpwm.bindings.app")


class Argument(object):
    def __init__(self, value):
        if '$' in value:
            # There's variable replacements, so we need to store a Template, and call .substitute() whenever called.
            self.template = Template(value)
            self.isTemplate = True

        else:
            self.value = self.expandPaths(value)
            self.isTemplate = False

    def __call__(self):
        try:
            return self.value
        except AttributeError:
            return self.substituted

    def __str__(self):
        try:
            return str(self.value)
        except AttributeError:
            return str(self.template.template)

    def __repr__(self):
        try:
            return repr(self.value)
        except AttributeError:
            return repr(self.template.template)

    @staticmethod
    def expandPaths(value):
        return os.path.expanduser(value) if value.startswith('~') else value

    @property
    def substituted(self):
        try:
            return self.value
        except AttributeError:
            replacements = defaultdict(str)
            replacements.update(os.environ)

            value = self.template.substitute(**replacements)
            return self.expandPaths(value)


class Command(object):
    @classmethod
    def parse(self, command):
        """Parse the given list or string into a Command.

        If a string is given, it is stripped of comments, and then split into a list of arguments using shlex.split.

        """
        if isinstance(command, basestring):
            command = ' '.join(cmd.split('#', 1)[0].strip()  # Strip comments
                    for cmd in command.split('\n'))
            command = shlex.split(command)

        if any(command):
            return Command(command)

    def __init__(self, args):
        self.args = [Argument(arg) for arg in args]
        self.isTemplated = any(arg.isTemplate for arg in self.args)

    @staticmethod
    def reprArguments(args):
        return ' '.join(repr(arg) for arg in args)

    def __repr__(self):
        if self.isTemplated:
            return '{} (substituted: {})'.format(
                    self.reprArguments(self.args),
                    self.reprArguments(arg.substituted for arg in self.args)
                    )
        else:
            return self.reprArguments(self.args)

    def __call__(self, **kwargs):
        logger.debug("Running command: %s", repr(self))
        command = [arg.substituted for arg in self.args]

        try:
            proc = subprocess.Popen(command, **kwargs)
        except:
            logger.exception("Error while starting command %r!", repr(command))
        else:
            logger.debug("Command started; PID: %r", proc.pid)

        return proc


def parseCommands(*commands):
    """Parse the given arguments into a list of command argument lists.

    If one string is given, escaped newlines are removed, and the string is split on remaining newlines into a list of
    commands. Each command is then passed to `Command.parse`.

    """
    if len(commands) == 1 and isinstance(commands[0], basestring):
        commands = commands[0].replace('\\\n', '').split('\n')  # Remove escaped newlines, then split.

    return filter(None, [Command.parse(cmd) for cmd in commands])  # Parse commands, and remove empty results.


def commandsRepr(commands):
    return '    ' + '\n    '.join(repr(command) for command in commands)


def startSingle(command, **kwargs):
    """Starts the given command using Popen in response to an event.

    The `wait` keyword arg may be specified to cause startup to pause until the command finishes running. Additional
    options may be passed to the Popen constructor as keyword args.

    """
    command = Command.parse(command)

    kwargs.setdefault('close_fds', True)
    waitForCompletion = kwargs.pop('wait', False)

    def start_(*event):
        logger.debug("Starting single command: %s", repr(command))
        proc = command(**kwargs)

        if waitForCompletion:
            logger.debug("Waiting for PID %r to finish...", proc.pid)
            if proc.wait() != 0:
                logger.warn("PID %r (command %s) returned non-zero exit status %r!",
                        proc.pid, repr(command), proc.returncode)
            else:
                logger.debug("PID %r exited normally.", proc.pid)

    return start_


def startParallel(*commands, **kwargs):
    """Starts the given set of commands in parallel using Popen in response to an event.

    Additional options may be passed to the Popen constructor through `kwargs`.

    """
    commands = parseCommands(*commands)

    kwargs.setdefault('close_fds', True)
    waitForCompletion = kwargs.pop('wait', False)

    def start_(*event):
        logger.debug("Starting command set:\n%s", commandsRepr(commands))

        procs = list()
        for command in commands:
            procs.append(command(**kwargs))

        logger.debug("Command set started; PIDs: %s",
                ', '.join(str(proc.pid) if proc else '<START FAILED>' for proc in procs))

        if waitForCompletion:
            logger.debug("Waiting for all commands in command set to finish...")

            for idx, proc in enumerate(procs):
                if proc is None:
                    continue

                if proc.returncode is None:
                    logger.debug("Waiting for PID %r to finish...", proc.pid)
                    proc.wait()
                else:
                    logger.debug("PID %r already finished.", proc.pid)

                if proc.returncode != 0:
                    logger.warn("PID %r (command: %s) returned non-zero exit status %r!",
                            proc.pid, repr(command), proc.returncode)
                else:
                    logger.debug("PID %r exited normally.", proc.pid)

            logger.debug("Command set finished.")

    return start_


def startSerial(*commands, **kwargs):
    """Starts the given sequence of commands in serial using Popen in response to an event.

    Additional options may be passed to the Popen constructor through `kwargs`.

    """
    commands = parseCommands(*commands)

    kwargs.setdefault('close_fds', True)
    waitForCompletion = kwargs.pop('wait', False)

    def start_(*event, **event_kwargs):
        log = event_kwargs.pop('logger', logger)

        log.debug("Starting command sequence:\n%s", commandsRepr(commands))

        for command in commands:
            proc = command(**kwargs)
            if proc.wait() != 0:
                logger.warn("PID %r (command: %s) returned non-zero exit status %r!",
                        proc.pid, repr(command), proc.returncode)
            else:
                logger.debug("PID %r exited normally.", proc.pid)

        logger.debug("Command sequence finished.")

    if waitForCompletion:
        return start_

    else:
        def start_wrapper_(*event):
            log = multiprocessing.get_logger()
            start_(*event, logger=log)

        def start_subprocess_(*event):
            multiprocessing.Process(target=start_wrapper_, args=event).start()

        return start_subprocess_
