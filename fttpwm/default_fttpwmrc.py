from os import chdir
from os.path import expanduser

from fttpwm.keyboard import bindKeys
from fttpwm.layout import Floating, Rows, Columns
from fttpwm.mouse import bindMouse
from fttpwm.themes import Default
import fttpwm.themes.fonts as fonts
import fttpwm.resources as resources
from fttpwm.themes.wallpaper import SVG
from fttpwm.bindings.app import startSingle, startParallel
from fttpwm.bindings.layout import Floating as FloatingBindings, setLayout, _RaiseWindow
from fttpwm.bindings.layout import moveNext, movePrevious, focusNext, focusPrevious
from fttpwm.bindings.wm import quit, switchWorkspace
import fttpwm.xdg.autostart as xdg_autostart


META = 'Mod4+'

bindKeys({
        META + 'Return': startSingle('urxvtc'),
        META + 'Control+Q': quit,
        META + '1': switchWorkspace(0),
        META + '2': switchWorkspace(1),
        META + '3': switchWorkspace(2),
        META + '4': switchWorkspace(3),
        META + '5': switchWorkspace(4),
        META + '6': switchWorkspace(5),
        META + '7': switchWorkspace(6),
        META + '8': switchWorkspace(7),
        META + '9': switchWorkspace(8),
        META + '0': switchWorkspace(9),
        META + 'bracketleft': switchWorkspace(10),
        META + 'bracketright': switchWorkspace(11),
        META + 'F': setLayout(Floating()),
        META + 'R': setLayout(Rows()),
        META + 'C': setLayout(Columns()),
        META + 'tab': FloatingBindings.nextWindow,
        META + 'Shift+tab': FloatingBindings.previousWindow,
        META + 'T': focusNext,
        META + 'N': focusPrevious,
        META + 'Shift+T': moveNext,
        META + 'Shift+N': movePrevious,
        })

bindMouse({
        '1': _RaiseWindow(),
        META + '1': FloatingBindings.raiseAndMoveWindow,
        META + '3': FloatingBindings.raiseAndResizeWindow,
        })

theme = Default()

fonts.options.set(
        antialias=fonts.antialias.default,
        hintMetrics=fonts.hintMetrics.on,
        hintStyle=fonts.hintStyle.slight,
        subpixelOrder=fonts.subpixelOrder.default,
        )

wallpaper = SVG(resources.fullPath('default-wallpaper.svg'))

enableStatusBar = True

# Startup
chdir(expanduser("~"))
autostart = [
        startSingle('xrdb .Xresources'),
        startParallel('''
            urxvtd -q -o

            # tiling window manager notification daemon
            # https://github.com/sboli/twmn
            twmnd

            # cairo-compmgr; pretty much just transparency iirc
            #cairo-compmgr

            # xcompmgr with soft shadows
            #xcompmgr -r 8 -l 5 -t 5 -o .7 -C -c

            # xcompmgr with no shadows
            xcompmgr -n
            '''),
        xdg_autostart.execute,
        ]
