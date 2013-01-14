from abc import ABCMeta, abstractmethod
import logging
import os.path

import cairo

from ..enum import Enum


logger = logging.getLogger("fttpwm.themes.wallpaper")


class ScaleMode(object):
    __metaclass__ = Enum
    _preferredNames = 'FitInside', 'FitOutside'

    Original = "Keep the source's original size."
    Full = "Scale the source to match the target exactly. (this will deform the pattern if they don't have the same " \
            "aspect ratio)"
    FitInside = FitLetterbox = "Scale the source, maintaining its aspect ratio, so that it's as large as possible " \
            "without any part extending past the target area."
    FitOutside = FitZoomed = "Scale the source, maintaining its aspect ratio, so that it's as small as possible " \
            "while still covering all areas of the target."
    FitWidth = "Scale the source, maintaining its aspect ratio, so that its width matches the target's."
    FitHeight = "Scale the source, maintaining its aspect ratio, so that its height matches the target's."


class ExtendMode(object):
    __metaclass__ = Enum
    _preferredNames = 'Tile', 'Nearest'

    NoExtend = "Don't extend outside the scaled area. (the remaining target area will be filled with the background " \
            "color)"
    Tile = Repeat = "Repeat the source to cover the taarget area."
    Reflect = "Reflect the source at its edges to cover the target area."
    Nearest = Smear = "Cover the target area with the value of the closest pixel from the source."


class Position(object):
    __metaclass__ = Enum

    Center = "Position the center of the source at the center of the target."
    Top = "Position the center of the source's top edge at the center of the target's top edge."
    Bottom = "Position the center of the source's bottom edge at the center of the target's bottom edge."
    Left = "Position the center of the source's left edge at the center of the target's left edge."
    Right = "Position the center of the source's right edge at the center of the target's right edge."
    TopLeft = "Position the top left corner of the source at the top left corner of the target."
    TopRight = "Position the top right corner of the source at the top right corner of the target."
    BottomLeft = "Position the bottom left corner of the source at the bottom left corner of the target."
    BottomRight = "Position the bottom right corner of the source at the bottom right corner of the target."


class BaseWallpaper(object):
    __metaclass__ = ABCMeta

    def __init__(self, *args, **kwargs):
        if args:
            logger.warn("BaseWallpaper: Unprocessed positional arguments: %r", args)
        if kwargs:
            logger.warn("BaseWallpaper: Unprocessed keyword arguments: %r", kwargs)

    @abstractmethod
    def paint(self, context, targetX, targetY, targetW, targetH):
        pass


class SolidColor(BaseWallpaper):
    def __init__(self, color=(0, 0, 0), *args, **kwargs):
        super(SolidColor, self).__init__(*args, **kwargs)
        self.color = color

    def paint(self, context, targetX, targetY, targetW, targetH):
        context.set_source_rgb(*self.color)
        context.paint()


class ScalableWallpaper(BaseWallpaper):
    def __init__(self, sourceSize=(1, 1), scaleMode=ScaleMode.Full, position=Position.Center, *args, **kwargs):
        super(ScalableWallpaper, self).__init__(*args, **kwargs)
        self.sourceSize = sourceSize
        self.scaleMode = scaleMode
        self.position = position

    def getScale(self, targetW, targetH):
        sourceW, sourceH = self.sourceSize
        resultW, resultH = self.getScaledSize(targetW, targetH)

        return float(resultW) / sourceW, float(resultH) / sourceH

    def getScaledSize(self, targetW, targetH):
        sourceW, sourceH = self.sourceSize
        scaleMode = self.scaleMode

        # If we're in FitInside or FitOutside mode, resolve the scaleMode to either FitWidth or FitHeight as
        # appropriate.
        if scaleMode == ScaleMode.FitInside:
            if float(targetW) / sourceW < float(targetH) / sourceH:
                scaleMode = ScaleMode.FitWidth
            else:
                scaleMode = ScaleMode.FitHeight

        elif scaleMode == ScaleMode.FitOutside:
            if float(targetW) / sourceW > float(targetH) / sourceH:
                scaleMode = ScaleMode.FitWidth
            else:
                scaleMode = ScaleMode.FitHeight

        # Now, calculate the actual resulting size.
        if scaleMode == ScaleMode.Original:
            return sourceW, sourceH

        elif scaleMode == ScaleMode.Full:
            return targetW, targetH

        elif scaleMode == ScaleMode.FitWidth:
            return targetW, float(targetW) / sourceW * targetH

        elif scaleMode == ScaleMode.FitHeight:
            return float(targetH) / sourceH * targetW, targetH


class CairoPattern(ScalableWallpaper):
    def __init__(self, pattern, extendMode=ExtendMode.NoExtend, *args, **kwargs):
        super(CairoPattern, self).__init__(*args, **kwargs)

        self.pattern = pattern
        self.extendMode = extendMode
        self.lastGeom = (0, 0, 1, 1)

    def paint(self, context, targetX, targetY, targetW, targetH):
        if self.lastGeom != (targetX, targetY, targetW, targetH):
            self.lastGeom = (targetX, targetY, targetW, targetH)
            self.pattern.set_matrix(self.getPatternMatrix(*self.lastGeom))

        context.set_source(self.pattern)
        context.paint()

    def getPatternMatrix(self, targetX, targetY, targetW, targetH):
        matrix = cairo.Matrix()
        matrix.translate(targetX, targetY)
        matrix.scale(*self.getScale(targetW, targetH))
        matrix.invert()
        return matrix


class PNG(CairoPattern):
    def __init__(self, filename, *args, **kwargs):
        image = cairo.ImageSurface.create_from_png(filename)
        pattern = cairo.SurfacePattern(image)
        super(PNG, self).__init__(pattern, sourceSize=(image.get_width(), image.get_height()), *args, **kwargs)


try:
    import rsvg

except ImportError:
    class SVG(SolidColor):
        def __init__(self, filename, *args, **kwargs):
            logger.error("Couldn't import 'rsvg'! Falling back to a black background.")
            super(SVG, self).__init__(*args, **kwargs)

else:
    class SVG(ScalableWallpaper):
        def __init__(self, filename, *args, **kwargs):
            if os.path.exists(filename):
                logger.info("Loading SVG wallpaper: %s", filename)
                self.svg = rsvg.Handle(file=filename)
                sourceSize = self.svg.get_properties('width', 'height')
            else:
                logger.warning("Specified SVG wallpaper %r does not exist!", filename)
                self.svg = None
                sourceSize = (0, 0)

            super(SVG, self).__init__(sourceSize=sourceSize, *args, **kwargs)

        def getContextMatrix(self, targetX, targetY, targetW, targetH):
            matrix = cairo.Matrix()
            matrix.translate(targetX, targetY)
            matrix.scale(*self.getScale(targetW, targetH))
            return matrix

        def paint(self, context, targetX, targetY, targetW, targetH):
            if self.svg is not None:
                context.set_matrix(self.getContextMatrix(targetX, targetY, targetW, targetH))
                self.svg.render_cairo(context)
