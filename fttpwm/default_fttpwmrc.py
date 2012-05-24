from fttpwm.keyboard import bindKeys
from fttpwm.mouse import bindMouse, raiseWindow, raiseAndMoveWindow, raiseAndResizeWindow
from fttpwm.utils import startApp, quit
from fttpwm.themes import Theme, State, Region, DefaultTitlebar
import fttpwm.themes.fonts as fonts


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

theme = Theme(
        focused=State(
            window=Region(
                opacity=1,
                ),
            titlebar=DefaultTitlebar(),
            border=Region(
                width=1,
                ),
            ),
        unfocused=State(
            window=Region(
                opacity=0.7,
                ),
            titlebar=DefaultTitlebar(bgFrom=(0.8, 0.7, 0.3), bgTo=(0.8, 0.5, 0.3)),
            border=Region(
                width=1,
                ),
            ),
        )

fonts.options.set(
        antialias=fonts.antialias.default,
        hintMetrics=fonts.hintMetrics.on,
        hintStyle=fonts.hintStyle.slight,
        subpixelOrder=fonts.subpixelOrder.default,
        )
