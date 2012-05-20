"""A simple Cairo/XCB sample application.

To exit the program, press 'Q' or 'Esc', or left-click on any window.
To force all windows to redraw, press 'R'.
To create a new window, press 'N'.

"""
import logging

import xcb
from xcb.xproto import Atom, CW, EventMask, PropMode, WindowClass
from xcb.xproto import ButtonPressEvent, EnterNotifyEvent, LeaveNotifyEvent, KeyPressEvent
from xcb.xproto import ExposeEvent, ConfigureNotifyEvent, MapNotifyEvent, UnmapNotifyEvent

import cairo


logger = logging.getLogger("test-cairo")


class App(object):
    """The main application object.

    This is responsible for the XCB connection, the run loop, and for handling events.

    """
    logger = logging.getLogger("test-cairo.App")

    def __init__(self):
        self.conn = xcb.connect()

        self.setup = self.conn.get_setup()
        self.screen = self.setup.roots[self.conn.pref_screen]
        self.root = self.screen.root
        self.depth = self.screen.root_depth
        self.visualID = self.screen.root_visual
        self.visual = self._findCurrentVisual()

        self.white = self.setup.roots[0].white_pixel
        self.black = self.setup.roots[0].black_pixel

        self.windows = dict()
        self.titlebar = Window(self, "This is a Python/Cairo/XCB example!")

        self._runLoop()

    def __getattr__(self, name):
        """Convenience to allow other classes to call into the connection without having to do self.app.conn._.

        """
        return getattr(self.conn, name)

    def _windowCreated(self, window):
        """Called by Window classes to notify the application of their existence.

        """
        self.windows[window.windowID] = window

    def _findCurrentVisual(self):
        """Find the VISUALTYPE object for our current visual.

        This is needed for initializing a Cairo XCBSurface.

        """
        for depth in self.screen.allowed_depths:
            if depth.depth == self.depth:
                for visual in depth.visuals:
                    if visual.visual_id == self.visualID:
                        return visual

    def _runLoop(self):
        """The main run loop - handles events from X or delegates them to existing Windows as needed.

        """
        while True:
            try:
                event = self.conn.wait_for_event()

            except xcb.ProtocolException as error:
                self.logger.debug("Protocol error %s received!", error.__class__.__name__)
                break

            except Exception as error:
                self.logger.debug("Unexpected error received: %s", error.message)
                break

            if isinstance(event, ExposeEvent):
                self._windowMethod(event.window, 'paint')

            elif isinstance(event, EnterNotifyEvent):
                self.logger.debug('Enter %r', (event.event_x, event.event_y))

            elif isinstance(event, LeaveNotifyEvent):
                self.logger.debug('Leave %r', (event.event_x, event.event_y))

            elif isinstance(event, ButtonPressEvent):
                button = event.detail
                self.logger.debug('Button %d down', button)
                if button == 1:
                    self.logger.info('Mouse button 1 pressed; exiting.')
                    break

            elif isinstance(event, KeyPressEvent):
                key = event.detail
                self.logger.debug('Key %s down; state: %r', key, event.state)

                if key == 53:
                    self.logger.info('"Q" pressed; exiting.')
                    break
                elif key == 9:
                    self.logger.info('"Esc" pressed; exiting.')
                    break
                elif key == 46:
                    self.logger.info('"N" pressed; creating new window.')
                    Window(self, "(A new window! Imagine that!)Oo.")
                elif key == 32:
                    self.logger.info('"R" pressed; redrawing all windows.')
                    for window in self.windows.values():
                        window.paint()

            elif isinstance(event, ConfigureNotifyEvent):
                self._debugEventContents(event)
                self._windowMethod(event.window, 'onConfigureNotify', event)

            elif isinstance(event, MapNotifyEvent):
                self._windowMethod(event.window, 'onMapped', event)

            elif isinstance(event, UnmapNotifyEvent):
                self._windowMethod(event.window, 'onUnmapped', event)

            else:
                self._debugEventContents(event)

        self.conn.disconnect()

    def _windowMethod(self, windowID, method, *args, **kwargs):
        window = self.windows[windowID]
        if hasattr(window, method):
            getattr(window, method)(*args, **kwargs)

    def _debugEventContents(self, event):
        """Log the contents of the given event.

        """
        self.logger.debug('\n'.join(
                ["Got {}:".format(type(event).__name__)]
                + ['  {}: {!r}'.format(attr, getattr(event, attr))
                    for attr in dir(event) if not attr.startswith('_')]
                ))

    def createWindow(self, x, y, width, height, attributes={}, windowID=None, parentID=None, borderWidth=0,
            windowClass=WindowClass.InputOutput, checked=False):
        """A convenience method to create new windows.

        The major advantage of this is the ability to use a dictionary to specify window attributes; this eliminates
        the need to figure out what order to specify values in according to the numeric values of the 'CW' enum members
        you're using.

        """
        if windowID is None:
            windowID = self.generate_id()

        if parentID is None:
            parentID = self.root

        attribMask = 0
        attribValues = list()

        # Values must be sorted by CW enum value, ascending.
        # Luckily, the tuples we get from dict.iteritems will automatically sort correctly.
        for attrib, value in sorted(attributes.iteritems()):
            attribMask |= attrib
            attribValues.append(value)

        if checked:
            call = self.core.CreateWindowChecked
        else:
            call = self.core.CreateWindow

        cookie = call(
                self.depth,
                windowID, parentID,
                x, y, width, height,
                borderWidth, windowClass,
                self.visualID,
                attribMask, attribValues
                )

        if checked:
            return windowID, cookie
        else:
            return windowID


class Window(object):
    """An example window using Cairo to draw itself.

    """
    def __init__(self, app, title):
        self.app = app
        self.title = title

        self.windowID = self.app.conn.generate_id()
        self.logger = logging.getLogger("test-cairo.Window.{}".format(self.windowID))
        self.app._windowCreated(self)

        x, y = 0, 0
        width, height = 640, 480
        self.width, self.height = width, height

        cookies = []

        # Create titlebar window.
        winAttribs = {
                #CW.OverrideRedirect: 1,
                CW.BackPixel: self.app.black,
                CW.EventMask: EventMask.KeyPress | EventMask.ButtonPress
                    | EventMask.EnterWindow | EventMask.LeaveWindow | EventMask.Exposure
                    | EventMask.StructureNotify  # gives us ConfigureNotify events
                }

        self.windowID, cookie = self.app.createWindow(
                x, y, width, height,
                attributes=winAttribs, windowID=self.windowID, checked=True
                )
        cookies.append(cookie)

        # Set window title.
        cookies.append(self.app.core.ChangePropertyChecked(
            PropMode.Replace, self.windowID, Atom.WM_NAME, Atom.STRING, 8,
            len(title), title
            ))

        # Set up Cairo.
        self.surface = cairo.XCBSurface(self.app.conn, self.windowID, self.app.visual, width, height)
        self.context = cairo.Context(self.surface)

        self.fontOptions = cairo.FontOptions()
        self.fontOptions.set_hint_metrics(cairo.HINT_METRICS_ON)

        # Show window.
        cookies.append(self.app.core.MapWindowChecked(self.windowID))

        # Flush the connection, and make sure all of our requests succeeded.
        self.app.flush()
        for cookie in cookies:
            cookie.check()

    def onConfigureNotify(self, event):
        if (self.width, self.height) != (event.width, event.height):
            # Window size changed; resize surface and redraw.
            self.logger.debug("Window size changed to {}.".format((event.width, event.height)))
            self.surface.set_size(event.width, event.height)
            self.width, self.height = event.width, event.height
            self.paint()

    def paint(self):
        self.logger.debug("Drawing...")
        self.context.set_operator(cairo.OPERATOR_OVER)

        linear = cairo.LinearGradient(0, 0, 0, self.height)
        linear.add_color_stop_rgba(0.00, 1, 0.9, 0, 1)
        linear.add_color_stop_rgba(1.00, 1, 0.3, 0, 1)
        self.context.set_source(linear)
        self.context.paint()

        self.context.set_source_rgb(0.0, 0.0, 0.0)
        self.context.select_font_face("drift", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        self.context.set_font_options(self.fontOptions)

        userFontEmSize, _ = self.context.device_to_user_distance(5, 0)
        self.context.set_font_size(userFontEmSize)

        x_bearing, y_bearing, width, height = self.context.text_extents(self.title)[:4]
        self.context.move_to(
                0.5 * self.width - width / 2 - x_bearing,
                0.5 * self.height - height / 2 - y_bearing)
        self.context.show_text(self.title)

        self.surface.flush()
        self.app.flush()


if __name__ == '__main__':
    print __doc__

    # Monochrome logging
    #logging.basicConfig(level=logging.NOTSET, format="[%(levelname)-8s] %(name)s:  %(message)s")

    # Color logging (*NIX only)
    logging.basicConfig(level=logging.NOTSET, format="{e}90m[{e}0;1m%(levelname)-8s{e}0;90m]{e}m "
            "{e}36m%(name)s{e}90m:{e}m  {e}2;3m%(message)s{e}m".format(e='\033['))

    App()
