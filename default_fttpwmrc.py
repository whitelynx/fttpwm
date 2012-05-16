from fttpwm.bind import bindKeys, bindMouse
from fttpwm.mouse import moveWindow, resizeWindow
from fttpwm.util import startApp


META = 'Mod3-'

bindKeys({
        META + 'Return': startApp('urxvt'),
        })

bindMouse({
        META + '1': moveWindow,
        META + '3': resizeWindow,
        })
