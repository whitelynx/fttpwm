from fttpwm.keyboard import bindKeys
from fttpwm.mouse import bindMouse, raiseWindow, raiseAndMoveWindow, raiseAndResizeWindow
from fttpwm.utils import startApp, quit


META = 'Mod4+'

bindKeys({
        META + 'Return': startApp('urxvt'),
        META + 'Control+Q': quit,
        })

bindMouse({
        '1': raiseWindow,
        META + '1': raiseAndMoveWindow,
        META + '3': raiseAndResizeWindow,
        })
