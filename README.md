Fast, Table-Tiling Python Window Manager (FTTPWM)
=================================================
_A (soon-to-be) flexible, configurable, and usable tiling window manager written in Python._

This WM does stuff. Not a lot yet, but it's getting... somewhere.


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
