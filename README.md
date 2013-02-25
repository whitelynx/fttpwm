Fast, Table-Tiling Python Window Manager (FTTPWM)
=================================================
_A (soon-to-be) flexible, configurable, and usable tiling window manager written in Python._

This WM does stuff. Not a lot yet, but it's getting... somewhere.

I will warn you: I don't yet consider this finished enough for _my own_ use. I definitely wouldn't suggest you try to
use this as your standard window manager yet.


Requirements
------------

- [Python][] version 2.6 or 2.7
- [xpyb][]
- [xpybutil][] (for now, use [my xpybutil fork][] until I get my changes finished and pulled into upstream)
- [py2cairo][] built with XCB support
- [pyzmq][] (theoretically optional, but you REALLY don't want to run without it)
- [python-rsvg][] (optional, but you won't be able to see the cool official FTTPWM wallpaper without it!)

[Python]: http://python.org
[xpyb]: http://pypi.python.org/pypi/xpyb/1.3.1
[xpybutil]: https://github.com/BurntSushi/xpybutil
[my xpybutil fork]: https://github.com/whitelynx/xpybutil
[py2cairo]: http://cairographics.org/pycairo
[pyzmq]: http://www.zeromq.org/bindings:python
[python-rsvg]: https://live.gnome.org/LibRsvg


Configuration
-------------
FTTPWM can be configured by creating a `~/.config/fttpwm/config.py` file; I suggest you copy `fttpwm/default_config.py`
and modify as needed.


Usage
-----
Because this is really light on features and probably pretty unstable at the moment, I suggest not using it as your
day-to-day window manager. If you still want to play around with it, Xephyr (or Xnest if you don't have Xephyr) works
quite well as a testbed:

	:::bash
	startx $(which python2) -m fttpwm -- $(which Xephyr) :1 -screen 1024x768


Coding Style
------------
For the most part, we adhere to [PEP 8][]. There are a couple of differences from PEP 8, however:

- **Maximum line length:** PEP 8 prescribes a limit of 79 characters. Given modern display resolutions (and the large
  amount of wasted space resulting from a 79-character width), we instead use a line length limit of 119 characters.
  This still allows me to fit two editors side-by-side on any of my screens, showing the full width of the code.
- **Breaking long lines:** PEP 8 says, "The preferred place to break around a binary operator is after the operator,
  not before it." We disagree; I find it easier to read line continuations when operators appear at the beginning of
  continued lines, especially in the case of functions which take multiple arguments, since the leading operator helps
  distinguish continued lines from new arguments.
- **Indentation:** We agree with everything specifically laid out by the actual PEP 8 document here, but the [pep8][]
  style checker app gives us a surprising number of errors dealing with indentation:
    - _E123 closing bracket does not match indentation of opening bracket's line_
    - _E124 closing bracket does not match visual indentation_
    - _E126 continuation line over-indented for hanging indent_
    - _E127 continuation line over-indented for visual indent_
    - _E128 continuation line under-indented for visual indent_

In order to check the FTTPWM code with the [pep8][] style checker app, we use the following command:

	:::bash
	pep8-python2 --max-line-length=119 --ignore=E123,E124,E126,E127,E128 .

[PEP 8]: http://www.python.org/dev/peps/pep-0008
[pep8]: https://pypi.python.org/pypi/pep8


License
-------
FTTPWM is released under the [MIT License][]. See the `LICENSE` file for details.

[MIT License]: http://opensource.org/licenses/MIT


Acknowledgements
----------------
FTTPWM's code was constructed with help from a variety of sources:

- Parts of [xpybutil][] (which is also a dependency) are overridden in order to correct certain behavior quirks. These
  changes really need to get merged back into the xpybutil codebase at some point.
- Code from several projects was used as a point of reference for FTTPWM, but I don't believe any code from them was
  directly copied: (if you find any copied code, let me know and I'll update this as appropriate!)
    - [awesome][]: Referenced for color parsing, basic selection handling, and clarification on the EWMH spec.
    - [feh][]: Referenced for setting the background.
    - [fluxbox][]: Referenced for setting the background.
    - [dwm][]: Referenced for several bits of functionality, mostly related to ICCCM and EWMH if I remember correctly.
- The [Xlib Programming Manual][], converted to HTML by [Christophe Tronche][], has been absolutely indispensible in
  understanding some of the more hairy aspects of programming using X11.
- Several [specifications from freedesktop.org][] have been used, whenever appropriate:
    - [XDG Base Directory Specification] version 0.6
    - [Inter-Client Communication Conventions Manual] version 2.0
    - [Extended Window Manager Hints] version 1.4.draft-2
    - [Desktop Entry Specification] version 1.0
    - [Desktop Application Autostart Specification] version 0.5
    - [D-Bus][] version 0.19 - has been pretty much the only guide for the D-Bus implementation in
      FTTPWM; I've looked at the existing libraries before, but I didn't reference them when writing this
      implementation.
    - [Desktop Notifications][] version 1.2

[awesome]: http://awesome.naquadah.org/
[feh]: https://github.com/derf/feh
[fluxbox]: http://fluxbox.org/
[dwm]: http://dwm.suckless.org/
[Xlib Programming Manual]: http://tronche.com/gui/x/xlib/
[Christophe Tronche]: http://tronche.com/

[specifications from freedesktop.org]: http://freedesktop.org/wiki/Specifications
[XDG Base Directory Specification]: http://freedesktop.org/wiki/Specifications/basedir-spec
[Inter-Client Communication Conventions Manual]: http://www.x.org/releases/X11R7.6/doc/xorg-docs/specs/ICCCM/icccm.html
[Extended Window Manager Hints]: http://freedesktop.org/wiki/Specifications/wm-spec
[Desktop Entry Specification]: http://standards.freedesktop.org/desktop-entry-spec/desktop-entry-spec-1.0.html
[Desktop Application Autostart Specification]: http://freedesktop.org/wiki/Specifications/autostart-spec
[D-Bus]: http://dbus.freedesktop.org/doc/dbus-specification.html
[Desktop Notifications]: http://people.gnome.org/~mccann/docs/notification-spec/notification-spec-latest.html
