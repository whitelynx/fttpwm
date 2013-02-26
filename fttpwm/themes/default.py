# -*- coding: utf-8 -*-
"""FTTPWM: Default theme

Copyright (c) 2012-2013 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import cairo

from ..paint import fonts
from ..paint.color import Color
from ..paint.context import pushContext, drawBevel, drawFill, drawText
from ..paint.gradients import linearGradient, Direction
from ..utils.geometry import Rect

from . import BaseTheme


class Default(BaseTheme):
    normal = dict(
            titlebarHeight=16,
            borderWidth=1,
            textColor=Color.rgb(0, 0, 0),
            fontFace="drift",
            fontSize=10,
            fontSlant=fonts.slant.normal,
            fontWeight=fonts.weight.normal,
            background=linearGradient(Direction.vertical, Color.rgb(.8, .7, .3), Color.rgb(.8, .5, .3)),
            innerBackground=None,
            opacity=.7,
            tabSpacing=1,
            )
    focused = dict(
            textColor=Color.rgb(1, 1, 1),
            background=linearGradient(Direction.vertical, Color.rgb(1, .9, 0), Color.rgb(1, .3, 0)),
            innerBackground=linearGradient(Direction.vertical, Color.rgba(0, 0, 0, .8), Color.rgba(0, 0, 0, .5)),
            opacity=1,
            )
    statusBar = dict(
            height=15,
            borderWidth=1,
            textColor=Color.rgba(1, 1, 1, .75),
            fontFace="lime",
            fontSize=10,
            fontSlant=fonts.slant.normal,
            fontWeight=fonts.weight.normal,
            background=linearGradient(Direction.vertical, Color('#362b00'), Color('#7c3100')),
            opacity=1,
            )

    def __init__(self):
        super(Default, self).__init__()

    def paintTab(self, ctx, frame, tabGeom=None):
        GFTV = lambda x: self.getFrameThemeValues(frame, *x.split())
        background, innerBackground, textColor, fontFace, fontSlant, fontWeight, fontSize, titlebarHeight = GFTV(
                'background innerBackground textColor fontFace fontSlant fontWeight fontSize titlebarHeight'
                )

        font = fonts.getFont(fontFace, fontSlant, fontWeight)

        if not tabGeom:
            tabGeom = Rect(0, 0, frame.width, titlebarHeight)
        elif not isinstance(tabGeom, Rect):
            tabGeom = Rect(*tabGeom)

        # Draw titlebar background
        drawFill(ctx, tabGeom, background)

        # Draw outer titlebar bevel
        drawBevel(ctx, tabGeom)

        with pushContext(ctx):
            innerGeom = tabGeom.shrink(36, 4)

            if innerBackground is not None:
                # Draw inner bevel
                drawBevel(ctx, innerGeom.grow(1, 1), sunken=True)

                # Draw title (inner) background
                drawFill(ctx, innerGeom, innerBackground)

            # Draw title text
            drawText(ctx, frame.title, innerGeom, textColor, font, fontSize)

    def paintWindow(self, ctx, frame, titleGeom=None):
        self.paintTab(ctx, frame, titleGeom)

    def paintStatusBarBackground(self, ctx, bar):
        background = self.getThemeValue('background', statusBar=True)

        # Draw titlebar background (and window border, since we're using ctx.paint instead of ctx.fill)
        background.set_matrix(cairo.Matrix(
                xx=1 / float(bar.width),
                yy=1 / float(bar.height)
                ))
        ctx.set_source(background)
        ctx.paint()

        # Draw outer titlebar bevel
        ctx.set_line_width(1)
        ctx.set_line_join(cairo.LINE_JOIN_MITER)
        ctx.set_line_cap(cairo.LINE_CAP_SQUARE)

        # ...highlight
        ctx.move_to(0.5, bar.height - 1.5)
        ctx.line_to(0.5, 0.5)
        ctx.line_to(bar.width - 1.5, 0.5)
        ctx.set_source_rgba(1, 1, 1, 0.3)
        ctx.stroke()

        # ...shadow
        ctx.move_to(bar.width - 0.5, 1.5)
        ctx.line_to(bar.width - 0.5, bar.height - 0.5)
        ctx.line_to(1.5, bar.height - 0.5)
        ctx.set_source_rgba(0, 0, 0, 0.3)
        ctx.stroke()

    def paintStatusBar(self, ctx, bar):
        GBTV = lambda x: self.getThemeValues(*x.split(), statusBar=True)
        textColor, fontFace, fontSlant, fontWeight, fontSize = GBTV(
                'textColor fontFace fontSlant fontWeight fontSize'
                )

        # Set up text drawing
        ctx.set_source_rgba(*textColor)
        ctx.select_font_face(fontFace, fontSlant, fontWeight)
        ctx.set_font_options(fonts.options.fontOptions)
        ctx.set_font_size(fontSize)

        # Draw title text
        align = fonts.Align(ctx, bar.width, bar.height)

        for pos, text in [
                (align.left, bar.leftText),
                (align.center, bar.centerText),
                (align.right, bar.rightText),
                ]:
            ctx.move_to(*pos(text))
            ctx.show_text(text)
