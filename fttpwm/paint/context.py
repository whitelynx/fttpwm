# -*- coding: utf-8 -*-
"""FTTPWM: Cairo context helpers

Copyright (c) 2012-2013 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from contextlib import contextmanager

import cairo

from .color import Color
from ..utils.geometry import Rect

from . import fonts


oddWidthStrokeMatrix = cairo.Matrix(x0=0.5, y0=0.5)


@contextmanager
def pushContext(context):
    context.save()
    yield
    context.restore()


def drawBevel(context, rect, highlightColor=Color.rgba(1, 1, 1, 0.3), shadowColor=Color.rgba(0, 0, 0, 0.3),
        strokeWidth=1, lineJoin=cairo.LINE_JOIN_MITER, lineCap=cairo.LINE_CAP_SQUARE, sunken=False):
    # Swap colors to create a sunken look if specified.
    if sunken:
        topLeftColor = shadowColor
        bottomRightColor = highlightColor
    else:
        topLeftColor = highlightColor
        bottomRightColor = shadowColor

    with pushContext(context):
        # Set line drawing options.
        context.set_line_width(strokeWidth)
        context.set_line_join(lineJoin)
        context.set_line_cap(lineCap)

        # If needed, line up the context so drawing at integral coordinates is aligned with pixels.
        if strokeWidth % 2:  # (if strokeWidth is odd)
            context.set_matrix(oddWidthStrokeMatrix)

        # ...top left
        context.move_to(*(rect.bottomLeft - (0, strokeWidth)))
        context.line_to(*rect.topLeft)
        context.line_to(*(rect.topRight - (strokeWidth, 0)))
        context.set_source_rgba(*topLeftColor)
        context.stroke()

        # ...bottom right
        context.move_to(*(rect.topRight + (0, strokeWidth)))
        context.line_to(*rect.bottomRight)
        context.line_to(*(rect.bottomLeft + (strokeWidth, 0)))
        context.set_source_rgba(*bottomRightColor)
        context.stroke()


def drawFill(context, rect, pattern, clip=True):
    with pushContext(context):
        if pattern is None:
            # If no pattern was given, assume we want to fill the area with transparent black.
            pattern = cairo.SolidPattern(0, 0, 0, 0.0)

        # Set a matrix to position and scale the pattern so it covers the given rect.
        fillMatrix = cairo.Matrix()
        fillMatrix.translate(*rect.topLeft)
        fillMatrix.scale(*rect.size)
        fillMatrix.invert()
        pattern.set_matrix(fillMatrix)

        if clip:
            context.rectangle(*rect)
            context.clip()

        # Paint the pattern.
        context.set_source(pattern)
        context.paint()


def drawText(context, text, rect=None, textColor=Color.rgb(0, 0, 0), font=None, fontSize=10.0,
        fontOptions=fonts.options.fontOptions, clip=True):

    with pushContext(context):
        if rect:
            context.rectangle(*rect)
            context.clip()

        # Set up title text drawing
        context.set_source_rgba(*textColor)

        if font:
            context.set_font_face(font)

        context.set_font_options(fonts.options.fontOptions)
        context.set_font_size(fontSize)

        if rect:
            if clip:
                # Set up clipping region.
                context.rectangle(*rect)
                context.clip()

            # Determine rendered text extents.
            textRect = Rect(*context.text_extents(text)[:4])

            # Position the current point to center the text in the given rect.
            context.move_to(*(rect.center - textRect.center))

        # Draw text
        context.show_text(text)
