from fttpwm.keyboard import bindKeys
from fttpwm.mouse import bindMouse, raiseWindow, moveWindow, resizeWindow
from fttpwm.utils import startApp, quit


META = 'Mod4+'

bindKeys({
        META + 'Return': startApp('urxvt'),
        META + 'Control+Q': quit,
        })

bindMouse({
        '1': raiseWindow,
        META + '1': moveWindow,
        META + '3': resizeWindow,
        })
