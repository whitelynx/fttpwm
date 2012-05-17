import shlex
import subprocess


def startapp(*command, **kwargs):
    """Starts the given command, returning the new process's PID.

    Additional options may be passed to the Popen constructor through `kwargs`.

    """
    if len(command) == 1 and isinstance(command[0], basestring):
        command = shlex.split(command[0])

    return subprocess.Popen(command, close_fds=True, **kwargs).pid
