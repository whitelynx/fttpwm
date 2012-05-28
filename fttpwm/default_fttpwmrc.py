from os import chdir
from os.path import expanduser

from fttpwm.keyboard import bindKeys
from fttpwm.mouse import bindMouse
from fttpwm.setroot import setWallpaper
from fttpwm.themes import Default
import fttpwm.themes.fonts as fonts
from fttpwm.bindings.app import startSingle, startParallel
from fttpwm.bindings.layout import Floating
from fttpwm.bindings.wm import quit, switchWorkspace


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
        })

bindMouse({
        '1': Floating.raiseWindow,
        META + '1': Floating.raiseAndMoveWindow,
        META + '3': Floating.raiseAndResizeWindow,
        })

theme = Default()

fonts.options.set(
        antialias=fonts.antialias.default,
        hintMetrics=fonts.hintMetrics.on,
        hintStyle=fonts.hintStyle.slight,
        subpixelOrder=fonts.subpixelOrder.default,
        )

# Startup
setWallpaper()
chdir(expanduser("~"))
autostart = [
        startSingle('xrdb .Xresources'),
        startParallel('''
            urxvtd -q -o

            # cairo-compmgr; pretty much just transparency iirc
            #cairo-compmgr

            # xcompmgr with soft shadows
            #xcompmgr -r 8 -l 5 -t 5 -o .7 -C -c

            # xcompmgr with no shadows
            xcompmgr -n
            '''),
        ]
