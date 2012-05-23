from argparse import Namespace
import logging

import cairo

from . import fonts, gradients


logger = logging.getLogger("fttpwm.themes.gradients")


class Theme(Namespace):
    pass


class State(Namespace):
    pass


class Region(Namespace):
    pass


class DefaultTitlebar(object):
    def __init__(self, height=16, textColor=(0, 0, 0), fontFace="drift", fontSize=5,
            fontSlant=fonts.slant.normal, fontWeight=fonts.weight.normal,
            bgFrom=(1, 0.9, 0), bgTo=(1, 0.3, 0), bgOrientation=gradients.Direction.vertical
            ):
        self.height = height

        self.gradient = cairo.LinearGradient(*bgOrientation)
        gradients.addColorStop(self.gradient, 0, bgFrom)
        gradients.addColorStop(self.gradient, 1, bgTo)

        if len(textColor) not in [3, 4]:
            logger.error("Invalid color: %r", self.textColor)

        self.textColor = textColor
        self.fontFace = fontFace
        self.fontSlant = fontSlant
        self.fontWeight = fontWeight
        self.fontSize = fontSize

    def __call__(self, ctx, frame):
        ctx.set_source(self.gradient)
        ctx.paint()

        if len(self.textColor) == 3:
            ctx.set_source_rgb(*self.textColor)
        elif len(self.textColor) == 4:
            ctx.set_source_rgba(*self.textColor)
        ctx.select_font_face(self.fontFace, self.fontSlant, self.fontWeight)
        ctx.set_font_options(fonts.options.fontOptions)

        userFontEmSize, _ = ctx.device_to_user_distance(self.fontSize, 0)
        ctx.set_font_size(userFontEmSize)

        xBearing, yBearing, textWidth, textHeight = ctx.text_extents(frame.title)[:4]
        ctx.move_to(
                0.5 - textWidth / 2 - xBearing,
                0.5 - textHeight / 2 - yBearing
                )
        ctx.show_text(frame.title)
