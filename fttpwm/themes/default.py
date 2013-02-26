# -*- coding: utf-8 -*-
"""FTTPWM: Default theme

Copyright (c) 2012-2013 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
import cairo

from ..paint import fonts
from ..paint.color import Color
from ..paint.context import pushContext
from ..paint.gradients import linearGradient, Direction

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

        if not tabGeom:
            tabGeom = [0, 0, frame.width, titlebarHeight]

        tabWidth, tabHeight = tabGeom[2:4]

        ctx.rectangle(*tabGeom)
        ctx.clip()

        # Draw titlebar background
        background.set_matrix(cairo.Matrix(
                xx=1 / float(tabWidth),
                yy=1 / float(tabHeight)
                ))
        ctx.set_source(background)
        ctx.paint()

        # Draw outer titlebar bevel
        ctx.set_line_width(1)
        ctx.set_line_join(cairo.LINE_JOIN_MITER)
        ctx.set_line_cap(cairo.LINE_CAP_SQUARE)

        # Line up the context so drawing at integral coordinates is aligned with pixels.
        with pushContext(ctx):
            ctx.set_matrix(self.strokeMatrix)

            # ...highlight
            ctx.move_to(0, tabHeight - 1)
            ctx.line_to(0, 0)
            ctx.line_to(tabWidth - 1, 0)
            ctx.set_source_rgba(1, 1, 1, 0.3)
            ctx.stroke()

            # ...shadow
            ctx.move_to(tabWidth, 1)
            ctx.line_to(tabWidth, tabHeight)
            ctx.line_to(1, tabHeight)
            ctx.set_source_rgba(0, 0, 0, 0.3)
            ctx.stroke()

            # Draw inner bevel
            if innerBackground is not None:
                # ...highlight
                ctx.move_to(tabWidth - 18, 3)
                ctx.line_to(tabWidth - 18, tabHeight - 2)
                ctx.line_to(19, tabHeight - 2)
                ctx.set_source_rgba(1, 1, 1, 0.3)
                ctx.stroke()

                # ...shadow
                ctx.move_to(17, tabHeight - 3)
                ctx.line_to(17, 1)
                ctx.line_to(tabWidth - 18, 1)
                ctx.set_source_rgba(0, 0, 0, 0.3)
                ctx.stroke()

                ctx.restore()
                ctx.save()

                # Draw title (inner) background
                innerBGMatrix = cairo.Matrix()
                innerBGMatrix.translate(2 + 16, 2)
                innerBGMatrix.scale(
                        tabWidth - 4 - 32,
                        tabHeight - 4,
                        )
                innerBGMatrix.invert()

                innerBackground.set_matrix(innerBGMatrix)
                ctx.set_source(innerBackground)

            with pushContext(ctx):
                # Clip the remainder of the background drawing to the title area.
                ctx.rectangle(2 + 16, 2, tabWidth - 4 - 32, tabHeight - 4)
                ctx.clip()

                if innerBackground is not None:
                    # Finish painting the inner background.
                    ctx.paint()

            # Set up title text drawing
            ctx.set_source_rgba(*textColor)
            ctx.select_font_face(fontFace, fontSlant, fontWeight)
            ctx.set_font_options(fonts.options.fontOptions)
            ctx.set_font_size(fontSize)

            # Draw title text
            title = frame.title
            width = tabWidth
            xBearing, yBearing, textWidth, textHeight = ctx.text_extents(title)[:4]
            ctx.move_to(
                    (width - textWidth) / 2 - xBearing,
                    (tabHeight - textHeight) / 2 - yBearing
                    )
            ctx.show_text(title)

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
