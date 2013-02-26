"""A simple Cairo/XCB benchmark to measure the performance of methods of rendering windows with text and gradients.

"""
from abc import ABCMeta, abstractmethod
import logging
import time
import timeit
import traceback
import random
import string
import sys

import xcb
from xcb.xproto import Atom, CW, EventMask, PropMode, WindowClass
from xcb.xproto import ExposeEvent, MapNotifyEvent, PropertyNotifyEvent

import cairo

import fttpwm.paint.fonts as fonts
from fttpwm.utils.x import findCurrentVisual


logger = logging.getLogger("cairo_bench")

conn = xcb.connect()


class BenchmarkCase(object):
    __metaclass__ = ABCMeta

    def __init__(self, iterations=100, repetitions=20):
        self.iterations = iterations
        self.repetitions = repetitions

    def run(self):
        logger.debug("Setting up %s.", self.__class__.__name__)
        timer = timeit.Timer(stmt=self, setup=self.setup)

        logger.debug("Running %s.", self.__class__.__name__)
        results = timer.repeat(self.repetitions, self.iterations)

        logger.debug("Cleaning up %s.", self.__class__.__name__)
        self.cleanup()

        logger.info("\033[1;32m%s:\033[0;32m Results for %s repetitions of %s iterations: \033[1;32m%r\033[m",
                self.__class__.__name__, self.repetitions, self.iterations, results)
        logger.info("\033[1;32m%s:\033[0;32m Minimum repetition: \033[1;33m%r\033[m",
                self.__class__.__name__, min(results))

        return results

    def setup(self):
        pass

    def cleanup(self):
        pass

    @abstractmethod
    def __call__(self):
        pass


class CheckedXCalls(object):
    checked = True

    def __init__(self, proto):
        self.__proto = proto
        self.lastCall = None
        self.lastStack = None

    def __getattr__(self, name):
        if self.checked:
            checkedName = name + 'Checked'
            if hasattr(self.__proto, checkedName):
                name = checkedName

            target = getattr(self.__proto, name)

            def callit(*args, **kwargs):
                #logger.debug("Calling %s(*%r, **%r).check()", checkedName, args, kwargs)
                result = target(*args, **kwargs).check()
                self.lastCall = "{}(*{}, **{})".format(checkedName, args, kwargs)
                self.lastStack = traceback.extract_stack()
                return result

            return callit

        return getattr(self.__proto, checkedName)


class BaseX11Case(BenchmarkCase):
    eventLoggingEnabled = False

    def __init__(self, width, height, *args, **kwargs):
        self.width = width
        self.height = height
        super(BaseX11Case, self).__init__(*args, **kwargs)

    def setup(self):
        #self.conn = xcb.connect()
        self.conn = conn
        self.core = CheckedXCalls(self.conn.core)

        self.conn_setup = self.conn.get_setup()
        self.screen = self.conn_setup.roots[self.conn.pref_screen]
        self.root = self.screen.root
        self.depth = self.screen.root_depth
        self.visualID = self.screen.root_visual
        self.visual = findCurrentVisual(self.screen, self.depth, self.visualID)

        self.white = self.screen.white_pixel
        self.black = self.screen.black_pixel

        self.eventsReceived = 0

        self.createWindow()
        self.setupWindow()

        # Show window.
        self.core.MapWindow(self.windowID)

        self.waitFor({
                PropertyNotifyEvent: self.windowID,
                MapNotifyEvent: self.windowID,
                ExposeEvent: self.windowID,
                })

    def cleanup(self):
        self.core.UnmapWindow(self.windowID)
        self.core.DestroyWindow(self.windowID)
        self.windowID = None
        self.sync()
        #self.conn.disconnect()

    def convertAttributes(self, attributes):
        attribMask = 0
        attribValues = list()

        # Values must be sorted by CW enum value, ascending.
        # Luckily, the tuples we get from dict.iteritems will automatically sort correctly.
        for attrib, value in sorted(attributes.iteritems()):
            attribMask |= attrib
            attribValues.append(value)

        return attribMask, attribValues

    def createWindow(self):
        self.windowID = self.conn.generate_id()

        attribMask, attribValues = self.convertAttributes({
                CW.OverrideRedirect: 1,  # Avoid any overhead of the WM creating a frame, reparenting us, drawing, etc.
                CW.BackPixel: self.black,
                CW.EventMask: EventMask.Exposure | EventMask.PropertyChange
                    | EventMask.StructureNotify  # gives us MapNotify events
                })

        self.core.CreateWindow(
                self.depth,
                self.windowID, self.root,
                0, 0, self.width, self.height,
                0, WindowClass.InputOutput,
                self.visualID,
                attribMask, attribValues
                )

        title = "{}: {}".format(__file__, self.__class__.__name__)
        self.core.ChangeProperty(PropMode.Append, self.windowID, Atom.WM_NAME, Atom.STRING, 8, len(title), title)

    def linearGradient(self, orientation, *colors):
        #logger.debug("Creating linear gradient: %r %r", orientation, colors)
        gradient = cairo.LinearGradient(*orientation)

        if len(colors) == 1 and isinstance(colors[0], dict):
            for position, color in sorted(colors[0].iteritems()):
                gradient.add_color_stop_rgba(position, *color)

        else:
            for index, color in enumerate(colors):
                position = float(index) / (len(colors) - 1)
                gradient.add_color_stop_rgba(position, *color)

        return gradient

    def sync(self):
        self.conn.flush()

        while True:
            try:
                event = self.conn.poll_for_event()
            except xcb.ProtocolException as e:
                logger.exception("%s.sync got exception after %s!", self.__class__.__name__, self.core.lastCall)
                traceback.print_stack()

                if hasattr(e.args[0], 'bad_value'):
                    logger.debug("Exception's bad_value: %r", e.args[0].bad_value)
                if hasattr(e.args[0], 'major_opcode'):
                    logger.debug("Exception's major_opcode: %r", e.args[0].major_opcode)
                if hasattr(e.args[0], 'minor_opcode'):
                    logger.debug("Exception's minor_opcode: %r", e.args[0].minor_opcode)

                print ''.join(traceback.format_list(self.core.lastStack))
                print dir(e), e.args, e.message
                print dir(e.args[0])

                sys.exit(1)
                break

            if not event:
                break

            self.eventsReceived += 1
            self.logEvent(event)

        #logger.debug("Synced.")

    def waitFor(self, events):
        #logger.debug("Waiting for events: %r", events)
        self.conn.flush()

        while True:
            try:
                event = self.conn.wait_for_event()
            except xcb.ProtocolException as e:
                logger.exception("%s.waitFor got exception after %s!", self.__class__.__name__, self.core.lastCall)
                traceback.print_stack()

                if hasattr(e.args[0], 'bad_value'):
                    logger.debug("Exception's bad_value: %r", e.args[0].bad_value)
                if hasattr(e.args[0], 'major_opcode'):
                    logger.debug("Exception's major_opcode: %r", e.args[0].major_opcode)
                if hasattr(e.args[0], 'minor_opcode'):
                    logger.debug("Exception's minor_opcode: %r", e.args[0].minor_opcode)

                print ''.join(traceback.format_list(self.core.lastStack))
                print dir(e), e.args, e.message
                print dir(e.args[0])

                sys.exit(1)
                break

            if not event:
                break

            self.eventsReceived += 1
            self.logEvent(event)

            if type(event) in events:
                window = events[type(event)]

                if window is None or event.window == window:
                    del events[type(event)]

                    if len(events) == 0:
                        #logger.debug("Got all awaited events; returning!")
                        return

    def logEvent(self, event):
        if self.eventLoggingEnabled:
            logger.debug('\n'.join(
                    ["Got {}:".format(type(event).__name__)]
                    + ['  {}: {!r}'.format(attr, getattr(event, attr))
                        for attr in dir(event) if not attr.startswith('_')]
                    ))

    @abstractmethod
    def __call__(self):
        """Override this in your benchmark class. At the END of your override, call this implementation.

        """
        # Make a no-op update to a property on the window, as a checkpoint.
        self.core.ChangeProperty(PropMode.Append, self.windowID, Atom.WM_NAME, Atom.STRING, 8, 0, "")

        # Flush the connection.
        self.conn.flush()

        # Process all waiting events, and block until we receive the event for our property modification.
        self.waitFor({
                PropertyNotifyEvent: self.windowID,
                })


class Cairo_AlwaysRedraw(BaseX11Case):
    strokeMatrix = cairo.Matrix(x0=0.5, y0=0.5)

    def setupWindow(self):
        self.setupWindowContext()
        self.setupWindowBackground(self.context)
        self.setupWindowText(self.context)

    def setupWindowContext(self):
        # Set up Cairo.
        self.surface = cairo.XCBSurface(self.conn, self.windowID, self.visual, self.width, self.height)
        self.context = cairo.Context(self.surface)

    def setupWindowBackground(self, context):
        context.set_line_width(1)
        context.set_line_join(cairo.LINE_JOIN_MITER)
        context.set_line_cap(cairo.LINE_CAP_SQUARE)

        self.background = self.linearGradient((0, 0, 0, 1), (1, .9, 0, 1), (1, 0, 0, 1))

    def setupWindowText(self, context):
        fontOptions = cairo.FontOptions()
        fontOptions.set_hint_metrics(cairo.HINT_METRICS_ON)

        fontFace = "drift"
        fontSlant = fonts.slant.normal
        fontWeight = fonts.weight.normal

        context.select_font_face(fontFace, fontSlant, fontWeight)
        context.set_font_options(fontOptions)
        context.set_font_size(5)

    def cleanup(self):
        self.context = None
        self.surface.finish()
        self.surface = None
        super(Cairo_AlwaysRedraw, self).cleanup()

    def __call__(self):
        self.paintBackground(self.context)
        self.paintText(self.context)
        BaseX11Case.__call__(self)

    def paintBackground(self, ctx):
        # Draw titlebar background
        self.background.set_matrix(cairo.Matrix(
                xx=1 / float(self.width),
                yy=1 / float(self.height)
                ))
        ctx.set_source(self.background)
        ctx.paint()

        # Line up the context so drawing at integral coordinates is aligned with pixels.
        ctx.save()
        ctx.set_matrix(self.strokeMatrix)

        # ...highlight
        ctx.move_to(0, self.height - 1)
        ctx.line_to(0, 0)
        ctx.line_to(self.width - 1, 0)
        ctx.set_source_rgba(1, 1, 1, 0.3)
        ctx.stroke()

        # ...shadow
        ctx.move_to(self.width, 1)
        ctx.line_to(self.width, self.height)
        ctx.line_to(1, self.height)
        ctx.set_source_rgba(0, 0, 0, 0.3)
        ctx.stroke()
        ctx.restore()

        ctx.get_group_target().flush()

    def paintText(self, ctx):
        # Clip the remainder of the drawing to the title area.
        ctx.save()
        ctx.rectangle(2 + 16, 2, self.width - 4 - 32, self.height - 4)
        ctx.clip()

        # Set up title text drawing
        ctx.set_source_rgba(0, 0, 0, 1)

        # Draw title text
        title = ''.join(random.choice(string.printable) for i in range(30))
        xBearing, yBearing, textWidth, textHeight = ctx.text_extents(title)[:4]
        ctx.move_to(
                (self.width - textWidth) / 2 - xBearing,
                (self.height - textHeight) / 2 - yBearing
                )
        ctx.show_text(title)

        ctx.restore()
        ctx.get_group_target().flush()


class Cairo_XPixmapCache_XRedraw(Cairo_AlwaysRedraw):
    def setupWindow(self):
        self.setupWindowContext()

        self.pixmapID = self.conn.generate_id()
        self.core.CreatePixmap(
                self.depth,
                self.pixmapID, self.windowID, self.width, self.height
                )

        pixmapSurface = cairo.XCBSurface(self.conn, self.pixmapID, self.visual, self.width, self.height)
        pixmapContext = cairo.Context(pixmapSurface)
        self.setupWindowBackground(pixmapContext)
        self.setupWindowText(pixmapContext)

        self.paintBackground(pixmapContext)
        pixmapSurface.flush()
        self.paintText(pixmapContext)

        pixmapSurface.finish()

        attribMask, attribValues = self.convertAttributes({
                CW.BackPixmap: self.pixmapID
                })
        self.core.ChangeWindowAttributes(self.windowID, attribMask, attribValues)

    def cleanup(self):
        self.core.FreePixmap(self.pixmapID)
        self.pixmapID = None
        super(Cairo_XPixmapCache_XRedraw, self).cleanup()

    def __call__(self):
        self.core.ClearArea(False, self.windowID, 0, 0, 0, 0)
        BaseX11Case.__call__(self)


class Cairo_XPixmapCache_CairoRedraw(Cairo_AlwaysRedraw):
    def setupWindow(self):
        self.setupWindowContext()

        self.pixmapID = self.conn.generate_id()
        self.core.CreatePixmap(
                self.depth,
                self.pixmapID, self.windowID, self.width, self.height
                )

        self.pixmapSurface = cairo.XCBSurface(self.conn, self.pixmapID, self.visual, self.width, self.height)
        pixmapContext = cairo.Context(self.pixmapSurface)
        self.setupWindowBackground(pixmapContext)
        self.setupWindowText(pixmapContext)

        self.paintBackground(pixmapContext)
        self.paintText(pixmapContext)

        self.pixmapPattern = cairo.SurfacePattern(self.pixmapSurface)

    def cleanup(self):
        self.pixmapPattern = None
        self.pixmapSurface.finish()
        self.pixmapSurface = None
        self.core.FreePixmap(self.pixmapID)
        self.pixmapID = None
        super(Cairo_XPixmapCache_CairoRedraw, self).cleanup()

    def __call__(self):
        self.context.set_source(self.pixmapPattern)
        self.context.paint()
        BaseX11Case.__call__(self)


class Cairo_CairoImageCache(Cairo_AlwaysRedraw):
    def setupWindow(self):
        self.setupWindowContext()

        self.imageSurface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.width, self.height)
        imageContext = cairo.Context(self.imageSurface)
        self.setupWindowBackground(imageContext)
        self.setupWindowText(imageContext)

        self.paintBackground(imageContext)
        self.paintText(imageContext)

        self.imagePattern = cairo.SurfacePattern(self.imageSurface)

    def cleanup(self):
        self.imagePattern = None
        self.imageSurface.finish()
        self.imageSurface = None
        super(Cairo_CairoImageCache, self).cleanup()

    def __call__(self):
        self.context.set_source(self.imagePattern)
        self.context.paint()
        BaseX11Case.__call__(self)


class Cairo_XPixmapCache_XRedraw_RedrawText(Cairo_AlwaysRedraw):
    def setupWindow(self):
        self.setupWindowContext()
        self.setupWindowText(self.context)

        self.pixmapID = self.conn.generate_id()
        self.core.CreatePixmap(
                self.depth,
                self.pixmapID, self.windowID, self.width, self.height
                )

        pixmapSurface = cairo.XCBSurface(self.conn, self.pixmapID, self.visual, self.width, self.height)
        pixmapContext = cairo.Context(pixmapSurface)
        self.setupWindowBackground(pixmapContext)

        self.paintBackground(pixmapContext)
        pixmapSurface.finish()

        attribMask, attribValues = self.convertAttributes({
                CW.BackPixmap: self.pixmapID
                })
        self.core.ChangeWindowAttributes(self.windowID, attribMask, attribValues)

    def cleanup(self):
        self.core.FreePixmap(self.pixmapID)
        self.pixmapID = None
        super(Cairo_XPixmapCache_XRedraw_RedrawText, self).cleanup()

    def __call__(self):
        self.surface.flush()
        self.core.ClearArea(False, self.windowID, 0, 0, 0, 0)
        self.surface.mark_dirty()
        self.paintText(self.context)
        BaseX11Case.__call__(self)


class Cairo_XPixmapCache_CairoRedraw_RedrawText(Cairo_AlwaysRedraw):
    def setupWindow(self):
        self.setupWindowContext()
        self.setupWindowText(self.context)

        self.pixmapID = self.conn.generate_id()
        self.core.CreatePixmap(
                self.depth,
                self.pixmapID, self.windowID, self.width, self.height
                )

        self.pixmapSurface = cairo.XCBSurface(self.conn, self.pixmapID, self.visual, self.width, self.height)
        pixmapContext = cairo.Context(self.pixmapSurface)
        self.setupWindowBackground(pixmapContext)

        self.paintBackground(pixmapContext)

        self.pixmapPattern = cairo.SurfacePattern(self.pixmapSurface)

    def cleanup(self):
        self.pixmapPattern = None
        self.pixmapSurface.finish()
        self.pixmapSurface = None
        self.core.FreePixmap(self.pixmapID)
        self.pixmapID = None
        super(Cairo_XPixmapCache_CairoRedraw_RedrawText, self).cleanup()

    def __call__(self):
        self.context.set_source(self.pixmapPattern)
        self.context.paint()
        self.paintText(self.context)
        BaseX11Case.__call__(self)


class Cairo_CairoImageCache_RedrawText(Cairo_AlwaysRedraw):
    def setupWindow(self):
        self.setupWindowContext()
        self.setupWindowText(self.context)

        self.imageSurface = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.width, self.height)
        imageContext = cairo.Context(self.imageSurface)
        self.setupWindowBackground(imageContext)

        self.paintBackground(imageContext)

        self.imagePattern = cairo.SurfacePattern(self.imageSurface)

    def cleanup(self):
        self.imagePattern = None
        self.imageSurface.finish()
        self.imageSurface = None
        super(Cairo_CairoImageCache_RedrawText, self).cleanup()

    def __call__(self):
        self.context.set_source(self.imagePattern)
        self.context.paint()
        self.paintText(self.context)
        BaseX11Case.__call__(self)


if __name__ == '__main__':
    print __doc__

    # Monochrome logging
    #logging.basicConfig(level=logging.NOTSET, format="[%(levelname)-8s] %(name)s:  %(message)s")

    # Color logging (*NIX only)
    logging.basicConfig(level=logging.NOTSET, format="{e}90m[{e}0;1m%(levelname)-8s{e}0;90m]{e}m "
            "{e}36m%(name)s{e}90m:{e}m  {e}2;3m%(message)s{e}m".format(e='\033['))

    width, height = 256, 32
    iterations = 500
    repetitions = 25
    for case in [
            Cairo_AlwaysRedraw(width, height, iterations, repetitions),
            #Cairo_XPixmapCache_XRedraw(width, height, iterations, repetitions),
            #Cairo_XPixmapCache_CairoRedraw(width, height, iterations, repetitions),
            #Cairo_CairoImageCache(width, height, iterations, repetitions),
            Cairo_XPixmapCache_XRedraw_RedrawText(width, height, iterations, repetitions),
            Cairo_XPixmapCache_CairoRedraw_RedrawText(width, height, iterations, repetitions),
            Cairo_CairoImageCache_RedrawText(width, height, iterations, repetitions),
            ]:
        case.run()
        time.sleep(0.2)
