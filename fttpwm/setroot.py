# -*- coding: utf-8 -*-
"""FTTPWM: Wallpaper (root pixmap) setter

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from argparse import Namespace
import logging
import struct

import xcb
from xcb.xproto import Atom, CW, CloseDown, Kill, PropMode

import cairo

from .settings import settings
from .themes.wallpaper import SVG
from .utils import convertAttributes, findCurrentVisual
from . import resources


logger = logging.getLogger("fttpwm.setroot")

settings.setDefaults(
        wallpaper=SVG(resources.fullPath('default-wallpaper.svg')),
        )


def setWallpaper():
    conn = xcb.connect()
    cookies = Namespace()

    def getAtom(name):
        return conn.core.InternAtom(True, len(name), name)

    def getOrCreateAtom(name):
        return conn.core.InternAtom(False, len(name), name)

    setup = conn.get_setup()
    screenNumber = conn.pref_screen
    screen = setup.roots[screenNumber]
    rootID = screen.root
    black = screen.black_pixel
    depth = screen.root_depth
    visualID = screen.root_visual
    visual = findCurrentVisual(screen, depth, visualID)
    screenWidth = screen.width_in_pixels
    screenHeight = screen.height_in_pixels

    #TODO: Be a bit more discriminate about what resources we're killing.
    conn.core.KillClientChecked(Kill.AllTemporary).check()
    conn.flush()

    xRootPmapIDProp = getOrCreateAtom("_XROOTPMAP_ID")
    esetrootPmapIDProp = getOrCreateAtom("ESETROOT_PMAP_ID")

    pixmapID = conn.generate_id()
    cookies.createPixmap = conn.core.CreatePixmapChecked(depth, pixmapID, rootID, screenWidth, screenHeight)

    conn.flush()

    # Set up Cairo.
    surface = cairo.XCBSurface(conn, pixmapID, visual, screenWidth, screenHeight)
    context = cairo.Context(surface)

    # Draw the background image.
    #TODO: Xinerama/XRandR support!
    settings.wallpaper.paint(context, 0, 0, screenWidth, screenHeight)

    surface.flush()
    conn.flush()

    # Set root window properties and background.
    packedPixmapID = struct.pack('I', pixmapID)
    cookies.setRootPmapIDProp = conn.core.ChangePropertyChecked(PropMode.Replace, rootID,
            xRootPmapIDProp.reply().atom, Atom.PIXMAP, 32, 1, packedPixmapID)
    cookies.setEsetrootPmapIDProp = conn.core.ChangePropertyChecked(PropMode.Replace, rootID,
            esetrootPmapIDProp.reply().atom, Atom.PIXMAP, 32, 1, packedPixmapID)

    # Doing these in one combined ChangeWindowAttributes call seems to make BackPixel overwrite BackPixmap, so...
    cookies.setBackPixel = conn.core.ChangeWindowAttributesChecked(rootID, *convertAttributes({
            CW.BackPixel: black
            }))
    cookies.setBackPixmap = conn.core.ChangeWindowAttributesChecked(rootID, *convertAttributes({
            CW.BackPixmap: pixmapID
            }))

    # Clear the root window to its new background.
    cookies.clearArea = conn.core.ClearAreaChecked(False, rootID, 0, 0, 0, 0)

    # Flush the connection, and make sure all of our requests succeeded.
    conn.flush()
    for name, cookie in cookies._get_kwargs():
        try:
            cookie.check()
        except:
            logger.exception("Error while checking results of %s query!", name)

    conn.core.SetCloseDownModeChecked(CloseDown.RetainTemporary).check()

    conn.flush()
    conn.disconnect()


if __name__ == '__main__':
    logging.basicConfig(level=logging.NOTSET)
    setWallpaper()
