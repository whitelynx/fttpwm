from os import chdir
from os.path import expanduser

from fttpwm.keyboard import bindKeys
from fttpwm.mouse import bindMouse, raiseWindow, raiseAndMoveWindow, raiseAndResizeWindow
from fttpwm.setroot import setWallpaper
from fttpwm.themes import Default
import fttpwm.themes.fonts as fonts
from fttpwm.utils import run, startApp, quit
from fttpwm.wm import WMBindings as WM


META = 'Mod4+'

bindKeys({
        META + 'Return': startApp('urxvt'),
        META + 'Control+Q': quit,
        META + '1': WM.switchWorkspace(0),
        META + '2': WM.switchWorkspace(1),
        META + '3': WM.switchWorkspace(2),
        META + '4': WM.switchWorkspace(3),
        META + '5': WM.switchWorkspace(4),
        META + '6': WM.switchWorkspace(5),
        META + '7': WM.switchWorkspace(6),
        META + '8': WM.switchWorkspace(7),
        META + '9': WM.switchWorkspace(8),
        META + '0': WM.switchWorkspace(9),
        META + 'bracketleft': WM.switchWorkspace(10),
        META + 'bracketright': WM.switchWorkspace(11),
        })

bindMouse({
        '1': raiseWindow,
        META + '1': raiseAndMoveWindow,
        META + '3': raiseAndResizeWindow,
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
map(run, (l.strip() for l in '''
xrdb .Xresources

# cairo-compmgr; pretty much just transparency iirc
#cairo-compmgr

# xcompmgr with soft shadows
#xcompmgr -r 8 -l 5 -t 5 -o .7 -C -c

# xcompmgr with no shadows
xcompmgr -n
'''.strip().split('\n')
    if len(l.split('#', 1)[0]) > 0))
