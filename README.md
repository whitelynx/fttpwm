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
- [xpybutil][]
- [py2cairo][] built with XCB support

[Python]: http://python.org
[xpyb]: http://pypi.python.org/pypi/xpyb/1.3.1
[xpybutil]: https://github.com/BurntSushi/xpybutil
[py2cairo]: http://cairographics.org/pycairo


Configuration
-------------
FTTPWM can be configured by creating a `~/.fttpwmrc.py` file; I suggest you copy `fttpwm/default_fttpwmrc.py` and
modify as needed.


Usage
-----
Because this is really light on features and probably pretty unstable at the moment, I suggest not using it as your
day-to-day window manager. If you still want to play around with it, Xephyr (or Xnest if you don't have Xephyr) works
quite well as a testbed:

	startx $(which python2) -m fttpwm -- $(which Xephyr) :1 -screen 1024x768


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
[The D-Bus Specification]: http://dbus.freedesktop.org/doc/dbus-specification.html
[The Desktop Notifications Specification]: http://people.gnome.org/~mccann/docs/notification-spec/notification-spec-latest.html
