"""Desktop Entry Specification support

This module aims to (partially) implement the Desktop Entry Specification version 1.1, available at:
http://standards.freedesktop.org/desktop-entry-spec/desktop-entry-spec-1.1.html

"""
from ConfigParser import RawConfigParser, NoSectionError, NoOptionError
import re
import shlex
import subprocess


class DesktopEntry(object):
    def __init__(self, filename):
        self.filename = filename
        self.parser = RawConfigParser()

        # Desktop entry files must be case-sensitive!
        self.parser.optionxform = str

        self.parser.read(filename)

        self.defaultGroup = DesktopEntryGroup(self.parser, u'Desktop Entry')

    def __getattr__(self, attr):
        return getattr(self.defaultGroup, attr)

    def __getitem__(self, name):
        return ActionGroup(self.parser, name)


class StringTransform(object):
    transformRE = re.compile(r'\\[sntr\\]')

    transformReplacements = {
            ur'\s': u' ',
            ur'\n': u'\n',
            ur'\t': u'\t',
            ur'\r': u'\r',
            ur'\\': u'\\'
            }

    def __init__(self, stringType):
        self.stringType = stringType

    def __call__(self, value):
        return self.transformRE.sub(lambda match: self.transformReplacements[match.group(0)], self.stringType(value))

stringTransform = StringTransform(str)
localestringTransform = StringTransform(unicode)


class StringListTransform(StringTransform):
    transformRE = re.compile(r'(\\[sntr\\;]|;)')

    transformReplacements = {
            ur'\;': u';'
            }
    transformReplacements.update(StringTransform.transformReplacements)

    def __call__(self, value):
        values = []
        accum = []
        for index, match in enumerate(self.transformRE.finditer(value)):
            if index % 2 == 0:
                if match.group(0) == ';':
                    joined = ''.join(accum)
                    accum = []

                    if len(joined) > 0:
                        values.append(joined)

                else:
                    accum.append(self.transformReplacements[match.group(0)])

            else:
                accum.append(match.group(0))

        return values

stringListTransform = StringListTransform(str)
localestringListTransform = StringListTransform(unicode)


class _FieldCodeReplacement(object):
    def __init__(self, group, filesOrURLs):
        self.group = group
        self.filesOrURLs = filesOrURLs

    def __call__(self, fcode):
        if fcode == '%f':
            #TODO: URL handling!
            #TODO: Multiple file/URL argument handling!
            # A single file name, even if multiple files are selected. The system reading the desktop entry should
            # recognize that the program in question cannot handle multiple file arguments, and it should should
            # probably spawn and execute multiple copies of a program for each selected file if the program is not
            # able to handle additional file arguments. If files are not on the local file system (i.e. are on HTTP or
            # FTP locations), the files will be copied to the local file system and %f will be expanded to point at the
            # temporary file. Used for programs that do not understand the URL syntax.
            return self.filesOrURLs[:1]

        elif fcode == '%F':
            #TODO: URL handling!
            # A list of files. Use for apps that can open several local files at once. Each file is passed as a
            # separate argument to the executable program.
            return self.filesOrURLs

        elif fcode == '%u':
            #TODO: Multiple file/URL argument handling!
            # A single URL. Local files may either be passed as file: URLs or as file path.
            return self.filesOrURLs[:1]

        elif fcode == '%U':
            # A list of URLs. Each URL is passed as a separate argument to the executable program. Local files may
            # either be passed as file: URLs or as file path.
            return self.filesOrURLs

        elif fcode == '%d':
            # Deprecated.
            return []

        elif fcode == '%D':
            # Deprecated.
            return []

        elif fcode == '%n':
            # Deprecated.
            return []

        elif fcode == '%N':
            # Deprecated.
            return []

        elif fcode == '%i':
            # The Icon key of the desktop entry expanded as two arguments, first --icon and then the value of the Icon
            # key. Should not expand to any arguments if the Icon key is empty or missing.
            try:
                return ['--icon', self.group.Icon]
            except (NoSectionError, NoOptionError):
                return []

        elif fcode == '%c':
            #TODO: Locale support!
            # The translated name of the application as listed in the appropriate Name key in the desktop entry.
            return [self.group.Name]

        elif fcode == '%k':
            # The location of the desktop file as either a URI (if for example gotten from the vfolder system) or a
            # local filename or empty if no location is known.
            return [self.group.filename]

        elif fcode == '%v':
            # Deprecated.
            return []

        elif fcode == '%m':
            # Deprecated.
            return []

        raise ValueError("Invalid field code %r!", fcode)


class Group(object):
    def __init__(self, parser, groupName):
        self.parser = parser
        self.groupName = groupName

    def value(self, key):
        return self.parser.get(self.groupName, key)

    def numeric(self, key):
        return self.parser.getfloat(self.groupName, key)

    def boolean(self, key):
        return self.parser.getboolean(self.groupName, key)

    def string(self, key):
        return stringTransform(self.value(key))

    def localestring(self, key):
        return localestringTransform(self.value(key))

    def stringList(self, key):
        return stringListTransform(self.value(key))

    def localestringList(self, key):
        return localestringListTransform(self.value(key))


class ActionGroup(Group):
    fieldCodeRE = re.compile(r'^%[a-zA-Z%]$')

    @property
    def Name(self):
        """Specific name of the application, for example "Mozilla".

        Required in: all
        Allowed in: all

        """
        return self.localestring(u'Name')

    @property
    def Icon(self):
        """Icon to display in file manager, menus, etc.

        Required in: none
        Allowed in: all

        From the spec:

             If the name is an absolute path, the given file will be used. If the name is not an absolute path, the
             algorithm described in the Icon Theme Specification will be used to locate the icon.

        """
        return self.localestring(u'Icon')

    @property
    def OnlyShowIn(self):
        """A list of strings identifying the environments that should display this desktop entry or action.

        Mutually exclusive with NotShowIn.

        Required in: none
        Allowed in: all

        For possible values see the Desktop Menu Specification.

        """
        return self.stringList(u'OnlyShowIn')

    @property
    def NotShowIn(self):
        """A list of strings identifying the environments that should not display this desktop entry or action.

        Mutually exclusive with OnlyShowIn.

        Required in: none
        Allowed in: all

        For possible values see the Desktop Menu Specification.

        """
        return self.stringList(u'NotShowIn')

    @property
    def Exec(self):
        """Program to execute, possibly with arguments.

        Required in: Application, Action
        Allowed in: Application, Action

        """
        return self.string(u'Exec')

    def getExec(self, filesOrURLs):
        r"""Retrieve the Exec key's value, as a list of command line arguments.

        From the spec:

            The Exec key must contain a command line. A command line consists of an executable program optionally
            followed by one or more arguments. The executable program can either be specified with its full path or
            with the name of the executable only. If no full path is provided the executable is looked up in the $PATH
            environment variable used by the desktop environment. The name or path of the executable program may not
            contain the equal sign ("="). Arguments are separated by a space.

            Arguments may be quoted in whole. If an argument contains a reserved character the argument must be quoted.
            The rules for quoting of arguments is also applicable to the executable name or path of the executable
            program as provided.

            Quoting must be done by enclosing the argument between double quotes and escaping the double quote
            character, backtick character ("`"), dollar sign ("$") and backslash character ("\") by preceding it with
            an additional backslash character. Implementations must undo quoting before expanding field codes and
            before passing the argument to the executable program. Reserved characters are space (" "), tab, newline,
            double quote, single quote ("'"), backslash character ("\"), greater-than sign (">"), less-than sign ("<"),
            tilde ("~"), vertical bar ("|"), ampersand ("&"), semicolon (";"), dollar sign ("$"), asterisk ("*"),
            question mark ("?"), hash mark ("#"), parenthesis ("(") and (")") and backtick character ("`").

            Note that the general escape rule for values of type string states that the backslash character can be
            escaped as ("\\") as well and that this escape rule is applied before the quoting rule. As such, to
            unambiguously represent a literal backslash character in a quoted argument in a desktop entry file requires
            the use of four successive backslash characters ("\\\\"). Likewise, a literal dollar sign in a quoted
            argument in a desktop entry file is unambiguously represented with ("\\$").

            A number of special field codes have been defined which will be expanded by the file manager or program
            launcher when encountered in the command line. Field codes consist of the percentage character ("%")
            followed by an alpha character. Literal percentage characters must be escaped as %%. Deprecated field codes
            should be removed from the command line and ignored. Field codes are expanded only once, the string that is
            used to replace the field code should not be checked for field codes itself.

            Command lines that contain a field code that is not listed in this specification are invalid and must not
            be processed, in particular implementations may not introduce support for field codes not listed in this
            specification. Extensions, if any, should be introduced by means of a new key.

            A command line may contain at most one %f, %u, %F or %U field code. If the application should not open any
            file the %f, %u, %F and %U field codes must be removed from the command line and ignored.

            Field codes must not be used inside a quoted argument, the result of field code expansion inside a quoted
            argument is undefined. The %F and %U field codes may only be used as an argument on their own.

        """
        replacement = _FieldCodeReplacement(self, filesOrURLs)
        rawValue = self.Exec
        split = shlex.split(rawValue)
        for arg in split:
            if self.fieldCodeRE.match(arg):
                for newarg in replacement(arg):
                    yield newarg
            else:
                yield arg

    def execute(self, *filesOrURLs, **kwargs):
        assert self.Type == u'Application'
        args = list(self.getExec(filesOrURLs))
        subprocess.Popen(args, bufsize=-1, **kwargs)


class DesktopEntryGroup(ActionGroup):
    @property
    def Type(self):
        """

        Required in: Application, Link, and Directory
        Allowed in: Application, Link, and Directory

        From the spec:

            This specification defines 3 types of desktop entries: Application (type 1), Link (type 2) and Directory
            (type 3). To allow the addition of new types in the future, implementations should ignore desktop entries
            with an unknown type.

        """
        return self.string(u'Type')

    @property
    def Version(self):
        """Version of the Desktop Entry Specification that the desktop entry conforms with.

        Required in: none
        Allowed in: Application, Link, and Directory

        From the spec:

             Entries that confirm with this version of the specification should use 1.0. Note that the version field is
             not required to be present.

        """
        return self.string(u'Version')

    @property
    def GenericName(self):
        """Generic name of the application, for example "Web Browser".

        Required in: none
        Allowed in: Application, Link, and Directory

        """
        return self.localestring(u'GenericName')

    @property
    def NoDisplay(self):
        """NoDisplay means "this application exists, but don't display it in the menus".

        Required in: none
        Allowed in: Application, Link, and Directory

        From the spec:

            This can be useful to e.g.  associate this application with MIME types, so that it gets launched from a
            file manager (or other apps), without having a menu entry for it (there are tons of good reasons for this,
            including e.g. the netscape -remote, or kfmclient openURL kind of stuff).

        """
        return self.boolean(u'NoDisplay')

    @property
    def Comment(self):
        """Tooltip for the entry, for example "View sites on the Internet".

        Required in: none
        Allowed in: Application, Link, and Directory

        From the spec:

             The value should not be redundant with the values of Name and GenericName.

        """
        return self.localestring(u'Comment')

    @property
    def Hidden(self):
        """Whether the user deleted this entry.

        Required in: none
        Allowed in: Application, Link, and Directory

        From the spec:

            Hidden should have been called Deleted. It means the user deleted (at his level) something that was present
            (at an upper level, e.g. in the system dirs). It's strictly equivalent to the .desktop file not existing at
            all, as far as that user is concerned. This can also be used to "uninstall" existing files (e.g. due to a
            renaming) - by letting make install install a file with Hidden=true in it.

        """
        return self.boolean(u'Hidden')

    @property
    def TryExec(self):
        """Path to an executable file on disk used to determine if the program is actually installed.

        Required in: none
        Allowed in: Application

        From the spec:

             If the path is not an absolute path, the file is looked up in the $PATH environment variable. If the file
             is not present or if it is not executable, the entry may be ignored (not be used in menus, for example).

        """
        return self.string(u'TryExec')

    @property
    def Path(self):
        """If entry is of type Application, the working directory to run the program in.

        Required in: none
        Allowed in: Application

        """
        return self.string(u'Path')

    @property
    def Terminal(self):
        """Whether the program runs in a terminal window.

        Required in: none
        Allowed in: Application

        """
        return self.boolean(u'Terminal')

    @property
    def Actions(self):
        """Identifiers for application actions.

        Required in: none
        Allowed in: Application

        From the spec:

             This can be used to tell the application to make a specific action, different from the default behavior.
             The Application actions section describes how actions work.

        """
        return self.stringList(u'Actions')

    @property
    def MimeType(self):
        """The MIME type(s) supported by this application.

        Required in: none
        Allowed in: Application

        """
        return self.stringList(u'MimeType')

    @property
    def Categories(self):
        """Categories in which the entry should be shown in a menu.

        Required in: none
        Allowed in: Application

        For possible values see the Desktop Menu Specification.

        """
        return self.stringList(u'Categories')

    @property
    def Keywords(self):
        """A list of strings which may be used in addition to other metadata to describe this entry.

        Required in: none
        Allowed in: Application

        From the spec:

             This can be useful e.g. to facilitate searching through entries. The values are not meant for display, and
             should not be redundant with the values of Name or GenericName.

        """
        return self.localestringList(u'Keywords')

    @property
    def StartupNotify(self):
        """

        Required in: none
        Allowed in: Application

        From the spec:

             If true, it is KNOWN that the application will send a "remove" message when started with the
             DESKTOP_STARTUP_ID environment variable set. If false, it is KNOWN that the application does not work with
             startup notification at all (does not shown any window, breaks even when using StartupWMClass, etc.). If
             absent, a reasonable handling is up to implementations (assuming false, using StartupWMClass, etc.). (See
             the Startup Notification Protocol Specification for more details).

        """
        return self.boolean(u'StartupNotify')

    @property
    def StartupWMClass(self):
        """

        Required in: none
        Allowed in: Application

        From the spec:

             If specified, it is known that the application will map at least one window with the given string as its
             WM class or WM name hint (see the Startup Notification Protocol Specification for more details).

        """
        return self.string(u'StartupWMClass')

    @property
    def URL(self):
        """The URL to access.

        Required in: none
        Allowed in: Link

        """
        return self.string(u'URL')

if __name__ == '__main__':
    DesktopEntry('/usr/share/applications/urxvtc.desktop').execute()
    DesktopEntry('/usr/share/applications/vlc.desktop').execute(*re.split(ur'\s*\n\s*',
            u'''/home/whitelynx/images/wallpaper/Year Zero/1024x768.jpg
                /home/whitelynx/images/wallpaper/Year Zero/wallpaper1_01.jpg
                /home/whitelynx/images/wallpaper/Year Zero/wallpaper2_01.jpg'''
            ))
