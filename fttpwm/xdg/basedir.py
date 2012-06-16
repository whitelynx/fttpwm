"""XDG Base Directory Specification support

This module aims to implement the XDG Base Directory Specification version 0.8, available at:
http://standards.freedesktop.org/basedir-spec/basedir-spec-0.8.html (apparently mislabeled as 0.7 in that page)

"""
import glob
import os
from os.path import dirname, expanduser, isdir, isfile, join, relpath


class FileFactory(object):
    DEFAULT = object()

    def __init__(self, baseDir, defaultMode='r'):
        self.baseDir = baseDir
        self.defaultMode = defaultMode

    def __call__(self, filename, mode=DEFAULT):
        if mode == self.DEFAULT:
            mode = self.defaultMode

        return file(join(self.baseDir, filename), mode)


class BaseDirManager(object):
    def __init__(self, homeVar, defaultHome, dirsVar=None, defaultDirs=''):
        self.home = os.environ.get(homeVar, expanduser(defaultHome))
        if dirsVar is None:
            self.dirs = []
        else:
            self.dirs = os.environ.get(dirsVar, expanduser(defaultDirs)).split(':')

    # From the spec:
    #   A specification that refers to $XDG_DATA_DIRS or $XDG_CONFIG_DIRS should define what the behaviour must be when
    #   a file is located under multiple base directories. It could, for example, define that only the file under the
    #   most important base directory should be used or, as another example, it could define rules for merging the
    #   information from the different files.

    def findFirstFile(self, filename):
        """Find the first existing file by this name in the configured base directories.

        Base directories are searched in order of importance.

        """
        for dir in [self.home] + self.dirs:
            fullpath = join(dir, filename)
            if isfile(fullpath):
                return fullpath

    def findAllFiles(self, filename):
        """Find the full paths of all existing files by this name in the configured base directories.

        Base directories are searched in order of importance.

        """
        filenames = []
        for dir in [self.home] + self.dirs:
            fullpath = join(dir, filename)
            if isfile(fullpath):
                filenames.append(fullpath)

        return filenames

    def getFiles(self, subdir, pattern=None):
        """Find the names of all existing files under the given subdirectory in the configured base directories.

        Base directories are searched in order of importance.

        """
        filenames = set()
        for dir in [self.home] + self.dirs:
            try:
                if pattern is not None:
                    filenames.update(relpath(absPath, dir)
                            for absPath in glob.glob(join(dir, subdir, pattern)))
                else:
                    filenames.update(os.listdir(join(dir, subdir)))
            except:
                pass

        return filenames

    def readFirstFile(self, filename, mode='r'):
        """Open the first existing file by this name in the configured base directories for reading.

        Base directories are searched in order of importance.

        """
        # We use findAllFiles instead of findFirstfile here so if there's an error opening the file, we can move on to
        # the next one.
        #
        # From the spec:
        #   When attempting to read a file, if for any reason a file in a certain directory is unaccessible, e.g.
        #   because the directory is non-existant, the file is non-existant or the user is not authorized to open the
        #   file, then the processing of the file in that directory should be skipped. If due to this a required file
        #   could not be found at all, the application may chose to present an error message to the user.
        for fullpath in self.findAllFiles(filename):
            try:
                return open(fullpath, mode)
            except:
                pass

    def writeFile(self, filename, mode='r'):
        """Create or open the given file under the HOME base directory.

        The containing directory is created if it does not exist.

        """
        # From the spec:
        #   If, when attempting to write a file, the destination directory is non-existant an attempt should be made
        #   to create it with permission 0700. If the destination directory exists already the permissions should not
        #   be changed. The application should be prepared to handle the case where the file could not be written,
        #   either because the directory was non-existant and could not be created, or for any other reason. In such
        #   case it may chose [sic] to present an error message to the user.
        fullpath = join(self.home, filename)
        if not isdir(dirname(fullpath)):
            os.makedirs(fullpath, 0700)

        return open(fullpath, mode)


# $XDG_DATA_HOME defines the base directory relative to which user specific data files should be stored. If
# $XDG_DATA_HOME is either not set or empty, a default equal to $HOME/.local/share should be used.

# $XDG_DATA_DIRS defines the preference-ordered set of base directories to search for data files in addition to the
# $XDG_DATA_HOME base directory. The directories in $XDG_DATA_DIRS should be seperated with a colon ':'.
# If $XDG_DATA_DIRS is either not set or empty, a value equal to /usr/local/share/:/usr/share/ should be used.
data = BaseDirManager('XDG_DATA_HOME', '~/.local/share', 'XDG_DATA_DIRS', '/usr/local/share:/usr/share')


# $XDG_CONFIG_HOME defines the base directory relative to which user specific configuration files should be stored. If
# $XDG_CONFIG_HOME is either not set or empty, a default equal to $HOME/.config should be used.

# $XDG_CONFIG_DIRS defines the preference-ordered set of base directories to search for configuration files in addition
# to the $XDG_CONFIG_HOME base directory. The directories in $XDG_CONFIG_DIRS should be seperated with a colon ':'.
# If $XDG_CONFIG_DIRS is either not set or empty, a value equal to /etc/xdg should be used.
config = BaseDirManager('XDG_CONFIG_HOME', '~/.config', 'XDG_CONFIG_DIRS', '/etc/xdg')


# The order of base directories denotes their importance; the first directory listed is the most important. When the
# same information is defined in multiple places the information defined relative to the more important base directory
# takes precedent. The base directory defined by $XDG_DATA_HOME is considered more important than any of the base
# directories defined by $XDG_DATA_DIRS. The base directory defined by $XDG_CONFIG_HOME is considered more important
# than any of the base directories defined by $XDG_CONFIG_DIRS.

# $XDG_CACHE_HOME defines the base directory relative to which user specific non-essential data files should be stored.
# If $XDG_CACHE_HOME is either not set or empty, a default equal to $HOME/.cache should be used.
cache = BaseDirManager('XDG_CACHE_HOME', '~/.cache')


# $XDG_RUNTIME_DIR defines the base directory relative to which user-specific non-essential runtime files and other
# file objects (such as sockets, named pipes, ...) should be stored. The directory MUST be owned by the user, and he
# MUST be the only one having read and write access to it. Its Unix access mode MUST be 0700.

# The lifetime of the directory MUST be bound to the user being logged in. It MUST be created when the user first logs
# in and if the user fully logs out the directory MUST be removed. If the user logs in more than once he should get
# pointed to the same directory, and it is mandatory that the directory continues to exist from his first login to his
# last logout on the system, and not removed in between. Files in the directory MUST not survive reboot or a full
# logout/login cycle.

# The directory MUST be on a local file system and not shared with any other system. The directory MUST by
# fully-featured by the standards of the operating system. More specifically, on Unix-like operating systems AF_UNIX
# sockets, symbolic links, hard links, proper permissions, file locking, sparse files, memory mapping, file change
# notifications, a reliable hard link count must be supported, and no restrictions on the file name character set
# should be imposed. Files in this directory MAY be subjected to periodic clean-up. To ensure that your files are not
# removed, they should have their access time timestamp modified at least once every 6 hours of monotonic time or the
# 'sticky' bit should be set on the file.

# If $XDG_RUNTIME_DIR is not set applications should fall back to a replacement directory with similar capabilities
# and print a warning message. Applications should use this directory for communication and synchronization purposes
# and should not place larger files in it, since it might reside in runtime memory and cannot necessarily be swapped
# out to disk.

#TODO: Implement something to better match the spec!
runtimeDir = os.environ.get('XDG_RUNTIME_DIR', os.path.expanduser('~/.cache'))
