"""A simple Cairo/XCB sample application.

To exit the program, press 'Q' or 'Esc', or left-click on any window.
To force all windows to redraw, press 'R'.
To create a new window, press 'N'.

"""
from abc import ABCMeta, abstractmethod
import logging
import timeit
import random
import string

import xcb
from xcb.xproto import Atom, CW, EventMask, PropMode, WindowClass
from xcb.xproto import ButtonPressEvent, EnterNotifyEvent, LeaveNotifyEvent, KeyPressEvent
from xcb.xproto import ExposeEvent, ConfigureNotifyEvent, MapNotifyEvent, UnmapNotifyEvent, PropertyNotifyEvent

import cairo

import fttpwm.themes.fonts as fonts
from fttpwm.utils import findCurrentVisual


logger = logging.getLogger("cairo_bench")


class BenchmarkCase(object):
    __metaclass__ = ABCMeta

    def __init__(self, iterations=100, repetitions=5):
        self.iterations = iterations
        self.repetitions = repetitions

    def run(self):
        print repr(self.setup)
        timer = timeit.Timer(stmt=self, setup=self.setup)

        results = timer.repeat(self.repetitions, self.iterations)

        self.cleanup()

        print "Results for {} repetitions of {} iterations: {}".format(self.repetitions, self.iterations, results)

        return results

    def setup(self):
        pass

    def cleanup(self):
        pass

    @abstractmethod
    def __call__(self):
        pass


class BaseX11Case(BenchmarkCase):
    eventLoggingEnabled = False

    def __init__(self, width, height, *args, **kwargs):
        self.width = width
        self.height = height
        super(BaseX11Case, self).__init__(*args, **kwargs)

    def setup(self):
        self.conn = xcb.connect()

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
        self.conn.core.MapWindow(self.windowID)
        #self.conn.core.MapWindowChecked(self.windowID).check()

        self.waitFor({
                MapNotifyEvent: self.windowID,
                PropertyNotifyEvent: self.windowID,
                ExposeEvent: self.windowID,
                })

    def cleanup(self):
        self.conn.disconnect()

    def createWindow(self):
        self.windowID = self.conn.generate_id()

        attribMask = 0
        attribValues = list()

        attributes = {
                CW.OverrideRedirect: 1,  # Avoid any overhead of the WM creating a frame, reparenting us, drawing, etc.
                CW.BackPixel: self.black,
                CW.EventMask: EventMask.Exposure | EventMask.PropertyChange
                    | EventMask.StructureNotify  # gives us MapNotify events
                }

        # Values must be sorted by CW enum value, ascending.
        # Luckily, the tuples we get from dict.iteritems will automatically sort correctly.
        for attrib, value in sorted(attributes.iteritems()):
            attribMask |= attrib
            attribValues.append(value)

        self.conn.core.CreateWindow(
                self.depth,
                self.windowID, self.root,
                0, 0, self.width, self.height,
                0, WindowClass.InputOutput,
                self.visualID,
                attribMask, attribValues
                )

        title = "{}: {}".format(__file__, self.__class__.__name__)
        self.conn.core.ChangeProperty(PropMode.Append, self.windowID, Atom.WM_NAME, Atom.STRING, 8, len(title), title)

    def linearGradient(self, orientation, *colors):
        logger.debug("Creating linear gradient: %r %r", orientation, colors)
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
        #logger.debug("Syncing X events...")
        self.conn.flush()

        event = self.conn.poll_for_event()
        while event:
            self.eventsReceived += 1
            self.logEvent(event)

            event = self.conn.poll_for_event()
        #logger.debug("Done syncing.")

    def waitFor(self, events):
        #logger.debug("Waiting for events: %r", events)
        self.conn.flush()

        event = self.conn.wait_for_event()
        while event:
            self.eventsReceived += 1
            self.logEvent(event)

            if type(event) in events:
                window = events[type(event)]

                if window is None or event.window == window:
                    del events[type(event)]

                    if len(events) == 0:
                        #logger.debug("Got all awaited events; returning!")
                        return

            event = self.conn.wait_for_event()

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
        self.conn.core.ChangeProperty(PropMode.Append, self.windowID, Atom.WM_NAME, Atom.STRING, 8, 0, "")

        # Flush the connection.
        self.conn.flush()

        # Process all waiting events, and block until we receive the event for our property modification.
        self.waitFor({
                PropertyNotifyEvent: self.windowID,
                })


class RawCairoCase(BaseX11Case):
    strokeMatrix = cairo.Matrix(x0=0.5, y0=0.5)

    def setupWindow(self):
        # Set up Cairo.
        self.surface = cairo.XCBSurface(self.conn, self.windowID, self.visual, self.width, self.height)
        self.context = cairo.Context(self.surface)

        self.fontOptions = cairo.FontOptions()
        self.fontOptions.set_hint_metrics(cairo.HINT_METRICS_ON)

        self.fontFace = "drift"
        self.fontSize = 5
        self.fontSlant = fonts.slant.normal
        self.fontWeight = fonts.weight.normal
        self.textColor = (1, 1, 1, 1)
        self.background = self.linearGradient((0, 0, 0, 1), (1, .9, 0, 1), (1, 0, 0, 1))
        self.opacity = 1

        self.context.select_font_face(self.fontFace, self.fontSlant, self.fontWeight)
        self.context.set_font_options(fonts.options.fontOptions)
        self.context.set_font_size(5)

        self.context.set_line_width(1)
        self.context.set_line_join(cairo.LINE_JOIN_MITER)
        self.context.set_line_cap(cairo.LINE_CAP_SQUARE)

    def __call__(self):
        self.paint(self.context)
        super(RawCairoCase, self).__call__()

    def paint(self, ctx):
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

        # Clip the remainder of the drawing to the title area.
        ctx.save()
        ctx.rectangle(2 + 16, 2, self.width - 4 - 32, self.height - 4)
        ctx.clip()

        ctx.restore()

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


if __name__ == '__main__':
    print __doc__

    # Monochrome logging
    #logging.basicConfig(level=logging.NOTSET, format="[%(levelname)-8s] %(name)s:  %(message)s")

    # Color logging (*NIX only)
    logging.basicConfig(level=logging.NOTSET, format="{e}90m[{e}0;1m%(levelname)-8s{e}0;90m]{e}m "
            "{e}36m%(name)s{e}90m:{e}m  {e}2;3m%(message)s{e}m".format(e='\033['))

    for case in [
            RawCairoCase(800, 600)
            ]:
        case.run()
