from fttpwm.keyboard import bindKeys
from fttpwm.mouse import bindMouse, raiseWindow, raiseAndMoveWindow, raiseAndResizeWindow
from fttpwm.utils import startApp, quit
from fttpwm.themes import Theme, State, Region
from fttpwm.themes.gradients import linearGradient, Direction
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
            titlebar=Region(
                font=("drift", fonts.slant.normal, fonts.weight.normal),
                font_size=5,
                text=(0, 0, 0),
                background=linearGradient(Direction.Vertical, (1, 0.9, 0, 1), (1, 0.3, 0, 1)),
                height=16,
                opacity=1,
                ),
            border=Region(
                width=1,
                ),
            ),
        unfocused=State(
            titlebar=Region(
                font=("drift", fonts.slant.normal, fonts.weight.normal),
                font_size=5,
                text=(0, 0, 0),
                background=linearGradient(Direction.Vertical, (1, 0.7, 0.3, 0.8), (1, 0.5, 0.3, 0.8)),
                height=16,
                opacity=0.7,
                ),
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
