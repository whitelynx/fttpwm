from fttpwm.keyboard import bindKeys
from fttpwm.mouse import bindMouse, moveWindow, resizeWindow
from fttpwm.util import startApp


META = 'Mod3-'

bindKeys({
        META + 'Return': startApp('urxvt'),
        })

bindMouse({
        META + '1': moveWindow,
        META + '3': resizeWindow,
        })
