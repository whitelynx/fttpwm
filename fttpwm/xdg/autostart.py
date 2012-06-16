"""Desktop Application Autostart Specification support

This module aims to implement the Desktop Application Autostart Specification version 0.5, available at:
http://standards.freedesktop.org/autostart-spec/autostart-spec-0.5.html

"""
from . import basedir, desktopentry


def getEntries():
    for filename in basedir.config.getFiles('autostart', '*.desktop'):
        entry = desktopentry.DesktopEntry(basedir.config.readFirstFile(filename))
        if entry.isEnabled:
            yield entry


def execute():
    for entry in getEntries():
        entry.execute()


if __name__ == '__main__':
    for entry in getEntries():
        print list(entry.getExec([]))
