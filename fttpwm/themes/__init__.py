from argparse import Namespace
import logging
import re

import xpybutil.ewmh as ewmh

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

    def __iter__(self):
        return iter((self.r, self.g, self.b, self.a))

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


class BaseTheme(object):
    def __init__(self):
        self.currentFrame = None

    def __getitem__(self, key):
        return self.getFrameThemeValue(self.currentFrame, key)

    def getFrameThemeValues(self, frame, *keys):
        return self.getThemeValues(*keys, focused=frame.focused)

    def getFrameThemeValue(self, frame, key):
        return self.getThemeValue(key, focused=frame.focused)

    def getThemeValues(self, *keys, **state):
        return tuple(
                self.getThemeValue(key, **state)
                for key in keys
                )

    def getThemeValue(self, key, focused=False):
        normalVal = self.normal[key]

        if focused:
            return self.focused.get(key, normalVal)

        return normalVal

    def getFrameSizes(self, frame):
        """Retrieve the frame sizes appropriate for the given frame's window.

        Returns a tuple of frame sizes: (left, right, top, bottom)

        The ordering of the results is meant to follow the ordering of _NET_FRAME_EXTENTS from the EWMH specification.

        """
        return self.getFrameThemeValues(frame, 'borderWidth', 'borderWidth', 'titlebarHeight', 'borderWidth')

    def getClientGeometry(self, frame):
        """Retrieve the desired window geometry for the given frame's window, relative to the frame.

        Returns a tuple: (x, y, width, height)

        The ordering of the results is meant to follow the ordering of XMoveResizeWindow and the convention for window
        geometry in X.

        """
        left, right, top, bottom = self.getFrameSizes(frame)
        return left, top, (frame.width - left - right), (frame.height - top - bottom)

    def apply(self, frame):
        ewmh.set_frame_extents(frame.clientWindowID, *self.getFrameSizes(frame))
        ewmh.set_wm_window_opacity(frame.frameWindowID, self.getFrameThemeValue(frame, 'opacity'))


class Default(BaseTheme):
    normal = dict(
            titlebarHeight=16,
            borderWidth=1,
            textColor=Color.rgb(0, 0, 0),
            fontFace="drift",
            fontSize=5,
            fontSlant=fonts.slant.normal,
            fontWeight=fonts.weight.normal,
            bgFrom=Color.rgb(0.8, 0.7, 0.3),
            bgTo=Color.rgb(0.8, 0.5, 0.3),
            bgOrientation=gradients.Direction.vertical,
            opacity=.7,
            )
    focused = dict(
            bgFrom=Color.rgb(1, 0.9, 0),
            bgTo=Color.rgb(1, 0.3, 0),
            opacity=1,
            )

    def __init__(self):
        super(Default, self).__init__()

        bgOrientation, bgFrom, bgTo = self.getThemeValues(*'bgOrientation bgFrom bgTo'.split())
        normalGradient = cairo.LinearGradient(*bgOrientation)
        normalGradient.add_color_stop_rgba(0, *bgFrom)
        normalGradient.add_color_stop_rgba(1, *bgTo)
        self.normal['gradient'] = normalGradient

        bgOrientation, bgFrom, bgTo = self.getThemeValues(*'bgOrientation bgFrom bgTo'.split(), focused=True)
        focusedGradient = cairo.LinearGradient(*bgOrientation)
        focusedGradient.add_color_stop_rgba(0, *bgFrom)
        focusedGradient.add_color_stop_rgba(1, *bgTo)
        self.focused['gradient'] = focusedGradient

    def paintWindow(self, ctx, frame):
        gradient, textColor, fontFace, fontSlant, fontWeight, fontSize, titlebarHeight = self.getFrameThemeValues(
                frame, *'gradient textColor fontFace fontSlant fontWeight fontSize titlebarHeight'.split())

        gradient.set_matrix(cairo.Matrix(
                xx=1 / float(frame.width),
                yy=1 / float(titlebarHeight)
                ))
        ctx.set_source(gradient)
        ctx.paint()

        ctx.set_source_rgba(*textColor)
        ctx.select_font_face(fontFace, fontSlant, fontWeight)
        ctx.set_font_options(fonts.options.fontOptions)
        ctx.set_font_size(fontSize)

        title = frame.title
        width = frame.width
        xBearing, yBearing, textWidth, textHeight = ctx.text_extents(title)[:4]
        ctx.move_to(
                (width - textWidth) / 2 - xBearing,
                (titlebarHeight - textHeight) / 2 - yBearing
                )
        ctx.show_text(title)

        ctx.set_line_width(1)
        ctx.set_line_join(cairo.LINE_JOIN_MITER)
        ctx.set_line_cap(cairo.LINE_CAP_SQUARE)

        ctx.new_path()
        ctx.move_to(0.5, titlebarHeight - 1.5)
        ctx.line_to(0.5, 0.5)
        ctx.line_to(frame.width - 1.5, 0.5)
        ctx.set_source_rgba(1, 1, 1, 0.3)
        ctx.stroke()

        ctx.move_to(frame.width - 0.5, 1.5)
        ctx.line_to(frame.width - 0.5, titlebarHeight - 0.5)
        ctx.line_to(1.5, titlebarHeight - 0.5)
        ctx.set_source_rgba(0, 0, 0, 0.3)
        ctx.stroke()
