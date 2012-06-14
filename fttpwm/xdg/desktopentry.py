"""Desktop Entry Specification support

This module aims to implement the Desktop Entry Specification version 1.1, available at:
http://standards.freedesktop.org/desktop-entry-spec/desktop-entry-spec-1.1.html

"""
from ConfigParser import RawConfigParser


class DesktopEntry(object):
    #FIXME: This is currently incomplete!

    def __init__(self, filename):
        self.parser = RawConfigParser()

        # Desktop entry files must be case-sensitive!
        self.parser.optionxform = str

        self.parser.read(filename)

    def __getattr__(self, name):
        return self.parser.get('Desktop Entry', name.capitalize())

    def execute(self):
        assert self.type == 'Application'
        self.Exec
