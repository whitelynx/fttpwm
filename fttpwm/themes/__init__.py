from argparse import Namespace
import logging
import re

import cairo

from . import fonts, gradients


logger = logging.getLogger("fttpwm.themes.gradients")


class Color(object):
    stringFormats = [
            (lambda x: float(int(x, 16)) / 0xF, re.compile(r'#(?P<r>\d)(?P<g>\d)(?P<b>\d)(?P<a>\d)?$')),
            (lambda x: float(int(x, 16)) / 0xFF, re.compile(r'#(?P<r>\d{2})(?P<g>\d{2})(?P<b>\d{2})(?P<a>\d{2})?$')),
            (lambda x: float(int(x, 16)) / 0xFFFF, re.compile(r'#(?P<r>\d{4})(?P<g>\d{4})(?P<b>\d{4})(?P<a>\d{4})?$')),
            ]

    def __init__(self, string=None):
        self.r, self.g, self.b, self.a = 0, 0, 0, 1

        if string:
            for conv, fmt in self.stringFormats:
                match = fmt.match(string)
                if match:
                    self.r, self.g, self.b = map(conv, match.group('r', 'g', 'b'))
                    if match.group('a') is not None:
                        self.a = conv(match.group('a'))

    @classmethod
    def rgb(cls, r, g, b):
        color = cls()
        color.r, color.g, color.b = r, g, b
        return color


class Theme(Namespace):
    pass


class State(Namespace):
    pass


class Region(Namespace):
    pass


class Default(object):
    normal = dict(
            titlebarHeight=16,
            textColor=Color.rgb(0, 0, 0),
            fontFace="drift",
            fontSize=5,
            fontSlant=fonts.slant.normal,
            fontWeight=fonts.weight.normal,
            bgFrom=Color.rgb(0.8, 0.7, 0.3),
            bgTo=Color.rgb(0.8, 0.5, 0.3),
            bgOrientation=gradients.Direction.vertical,
            )
    focused = dict(
            bgFrom=Color.rgb(1, 0.9, 0),
            bgTo=Color.rgb(1, 0.3, 0),
            )

    def __init__(self):
        normalGradient = cairo.LinearGradient(*self.getThemeValue('bgOrientation'))
        gradients.addColorStop(normalGradient, 0, self.getThemeValue('bgFrom'))
        gradients.addColorStop(normalGradient, 1, self.getThemeValue('bgTo'))
        self.normal['gradient'] = normalGradient

        focusedGradient = cairo.LinearGradient(*self.getThemeValue('bgOrientation', True))
        gradients.addColorStop(focusedGradient, 0, self.getThemeValue('bgFrom', True))
        gradients.addColorStop(focusedGradient, 1, self.getThemeValue('bgTo', True))
        self.focused['gradient'] = focusedGradient

    def __getitem__(self, key):
        return self.getThemeValue(key, self.currentFrame.focused)

    def getThemeValue(self, key, focused=False):
        normalVal = self.normal[key]

        if focused:
            return self.focused.get(key, normalVal)

        return normalVal

    def paintWindow(self, ctx, frame):
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
