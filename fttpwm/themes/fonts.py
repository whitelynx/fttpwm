from argparse import Namespace

import cairo


Font = cairo.ToyFontFace

slant = Namespace(
        normal=cairo.FONT_SLANT_NORMAL,
        italic=cairo.FONT_SLANT_ITALIC,
        oblique=cairo.FONT_SLANT_OBLIQUE,
        )

weight = Namespace(
        normal=cairo.FONT_WEIGHT_NORMAL,
        bold=cairo.FONT_WEIGHT_BOLD,
        )

antialias = Namespace(
        default=cairo.ANTIALIAS_DEFAULT,
        none=cairo.ANTIALIAS_NONE,
        gray=cairo.ANTIALIAS_GRAY,
        subpixel=cairo.ANTIALIAS_SUBPIXEL,
        )

hintMetrics = Namespace(
        default=cairo.HINT_METRICS_DEFAULT,
        off=cairo.HINT_METRICS_OFF,
        on=cairo.HINT_METRICS_ON,
        )

hintStyle = Namespace(
        default=cairo.HINT_STYLE_DEFAULT,
        none=cairo.HINT_STYLE_NONE,
        slight=cairo.HINT_STYLE_SLIGHT,
        medium=cairo.HINT_STYLE_MEDIUM,
        full=cairo.HINT_STYLE_FULL,
        )

subpixelOrder = Namespace(
        default=cairo.SUBPIXEL_ORDER_DEFAULT,
        rgb=cairo.SUBPIXEL_ORDER_RGB,
        bgr=cairo.SUBPIXEL_ORDER_BGR,
        vrgb=cairo.SUBPIXEL_ORDER_VRGB,
        vbgr=cairo.SUBPIXEL_ORDER_VBGR,
        )


class _FontOptions(object):
    __features = {
            "antialias": "antialias",
            "hint_metrics": "hintMetrics",
            "hint_style": "hintStyle",
            "subpixel_order": "subpixelOrder",
            }

    def __init__(self):
        self.fontOptions = cairo.FontOptions()

        for cairoName, friendlyName in self.__features.iteritems():
            setattr(self, friendlyName, property(
                    fget=getattr(self.fontOptions, 'get_' + cairoName),
                    fset=getattr(self.fontOptions, 'set_' + cairoName),
                    doc="Set the global {} font option".format(cairoName.replace('_', ' '))
                    ))

    def set(self, **kwargs):
        for feature, value in kwargs.iteritems():
            setattr(self, feature, value)


options = _FontOptions()
