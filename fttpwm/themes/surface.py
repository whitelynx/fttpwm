"""FTTPWM: Cairo surface helper classes

Copyright (c) 2012 David H. Bronke
Licensed under the MIT license; see the LICENSE file for details.

"""
from abc import ABCMeta, abstractmethod

from xcb.xproto import CW, EventMask

import xpybutil
import xpybutil.event

import cairo

from .. import singletons
from ..settings import settings


class CacheableCairoSurface(object):
    __metaclass__ = ABCMeta

    def __init__(self, width, height, targetDrawableID=None):
        self.width = width
        self.height = height
        self.mapped = False
        self.cleanUpTarget = False

        if targetDrawableID is None:
            # Create a basic window for the target.
            self.windowAttribs = {
                    CW.OverrideRedirect: 1,
                    CW.BackPixel: singletons.x.black,
                    CW.EventMask: EventMask.Exposure | EventMask.PropertyChange
                        | EventMask.StructureNotify  # gives us MapNotify events
                    }
            targetDrawableID = singletons.x.createWindow(0, 0, self.width, self.height, attributes=self.windowAttribs)
            self.cleanUpTarget = True

            xpybutil.window.listen(targetDrawableID, 'ButtonPress', 'Exposure', 'PropertyChange', 'StructureNotify')

        xpybutil.event.connect('ConfigureNotify', targetDrawableID, self.onConfigureNotify)
        xpybutil.event.connect('Expose', targetDrawableID, self.onExpose)
        xpybutil.event.connect('MapNotify', targetDrawableID, self.onMapNotify)
        xpybutil.event.connect('UnmapNotify', targetDrawableID, self.onUnmapNotify)

        self.targetDrawableID = targetDrawableID

    def cleanup(self):
        if self.targetDrawableID is not None:
            self.onCleanup()
        self.targetDrawableID = None

    def paint(self):
        if self.mapped:
            self.onPaint()

    def onConfigureNotify(self, event):
        self.onResize(event.width, event.height)

    def onExpose(self, event):
        # A count of 0 denotes the last Expose event in a series of contiguous Expose events; this check lets us
        # collapse such series into a single call to paint() so we don't get extraneous redraws.
        if event.count == 0:
            self.wm.callWhenQueueEmpty(self.paint)

    def onMapNotify(self, event):
        self.mapped = True

    def onUnmapNotify(self, event):
        self.mapped = False

    # To be (re)implemented by the intermediate surface subclasses below, which provide the caching implementation.
    @abstractmethod
    def onSetup(self):
        pass

    @abstractmethod
    def onCleanup(self):
        if self.cleanUpTarget:
            self.core.UnmapWindow(self.targetDrawableID)
            self.core.DestroyWindow(self.targetDrawableID)

    @abstractmethod
    def onPaint(self):
        pass

    @abstractmethod
    def onResize(self, newWidth, newHeight):
        self.width = newWidth
        self.height = newHeight

    @abstractmethod
    def updateBackground(self):
        pass

    @abstractmethod
    def updateForeground(self):
        pass

    # To be implemented by the final surface subclass, which provides the actual drawing logic.
    @abstractmethod
    def setupBackground(self, context):
        pass

    @abstractmethod
    def setupForeground(self, context):
        pass

    @abstractmethod
    def drawBackground(self, context):
        pass

    @abstractmethod
    def drawForeground(self, context):
        pass


class NoCachingSurface(CacheableCairoSurface):
    """Perform no caching, instead redrawing from scratch for every onPaint call.

    """
    def onSetup(self):
        # Set up Cairo context for the target window.
        self.surface = cairo.XCBSurface(
                xpybutil.conn, self.targetDrawableID, singletons.x.visual, self.width, self.height)
        self.context = cairo.Context(self.surface)

        self.setupBackground(self.context)
        self.setupForeground(self.context)

        self.paint()

    def onCleanup(self):
        self.context = None
        self.surface.finish()
        self.surface = None
        super(NoCachingSurface, self).onCleanup()

    def onPaint(self):
        #FIXME: Track whether or not this surface is visible, and don't repaint if it's not!
        self.drawBackground(self.context)
        self.drawForeground(self.context)

    def onResize(self, newWidth, newHeight):
        super(NoCachingSurface, self).onResize(newWidth, newHeight)

        # Window size changed; resize surface and redraw.
        self.surface.set_size(newWidth, newHeight)
        self.paint()

    def updateBackground(self):
        self.paint()

    def updateForeground(self):
        self.paint()


class XPixmapSurface(CacheableCairoSurface):
    """Cache to an X pixmap, and redraw the window by clearing it with X.

    """
    resizeThreshold = 20

    def onSetup(self):
        self.setupPixmaps(self.width, self.height)
        self.paint()

    def setupPixmaps(self, width, height):
        self.createPixmaps(width, height)

        attribMask, attribValues = self.convertAttributes({
                CW.BackPixmap: self.combinedPixmapID
                })
        xpybutil.conn.core.ChangeWindowAttributes(self.targetDrawableID, attribMask, attribValues)

    def createPixmaps(self, width, height):
        self.pixmapWidth = width
        self.pixmapHeight = height

        # Set up background pixmap.
        self.backgroundPixmapID = self.conn.generate_id()
        xpybutil.conn.core.CreatePixmap(
                singletons.x.depth, self.backgroundPixmapID, self.targetDrawableID, width, height)

        self.backgroundSurface = cairo.XCBSurface(
                xpybutil.conn, self.backgroundPixmapID, singletons.x.visual, width, height)
        self.backgroundContext = cairo.Context(self.backgroundSurface)

        self.setupBackground(self.backgroundContext)
        self.drawBackground(self.backgroundContext)
        self.backgroundSurface.flush()

        self.backgroundPattern = cairo.SurfacePattern(self.backgroundSurface)

        # Set up combined pixmap.
        self.combinedPixmapID = self.conn.generate_id()
        xpybutil.conn.core.CreatePixmap(self.depth, self.combinedPixmapID, self.targetDrawableID, width, height)

        self.combinedSurface = cairo.XCBSurface(
                xpybutil.conn, self.combinedPixmapID, singletons.x.visual, width, height)
        self.combinedContext = cairo.Context(self.combinedSurface)

        self.setupForeground(self.combinedContext)
        self.combinedContext.set_source(self.backgroundPattern)
        self.combinedContext.paint()
        self.drawForeground(self.combinedContext)
        self.combinedSurface.flush()

    def destroyPixmaps(self):
        self.combinedContext = None
        self.combinedSurface.finish()
        self.combinedSurface = None

        self.backgroundContext = None
        self.backgroundSurface.finish()
        self.backgroundSurface = None

        xpybutil.conn.core.FreePixmap(self.backgroundPixmapID)
        self.backgroundPixmapID = None

    def onCleanup(self):
        self.destroyPixmaps()
        super(XPixmapSurface, self).onCleanup()

    def onPaint(self):
        #FIXME: Track whether or not this surface is visible, and don't repaint if it's not!
        xpybutil.conn.core.ClearArea(False, self.targetDrawableID, 0, 0, 0, 0)

    def onResize(self, newWidth, newHeight):
        # Don't bother resizing the pixmaps if we're within the resize threshold.
        rst = self.resizeThreshold
        if newWidth > self.pixmapWidth or newHeight > self.pixmapHeight \
                or newWidth + 2 * rst < self.pixmapWidth or newHeight + 2 * rst < self.pixmapHeight:
            self.destroyPixmaps()
            super(XPixmapSurface, self).onResize(newWidth, newHeight)
            self.setupPixmaps(newWidth + rst, newHeight + rst)
            self.paint()

        else:
            super(XPixmapSurface, self).onResize(newWidth, newHeight)
            self.updateBackground()

    def updateBackground(self):
        self.drawBackground(self.backgroundContext)
        self.backgroundSurface.flush()
        self.updateForeground()

    def updateForeground(self):
        self.combinedContext.set_source(self.backgroundPattern)
        self.combinedContext.paint()
        self.drawForeground(self.combinedContext)
        self.combinedSurface.flush()
        self.paint()


class CairoPixmapSurface(XPixmapSurface):
    """Cache to an X pixmap, and redraw the window using Cairo. (default)

    """
    def onSetup(self):
        # Set up Cairo context for the target window.
        self.surface = cairo.XCBSurface(
                xpybutil.conn, self.targetDrawableID, singletons.x.visual, self.width, self.height)
        self.context = cairo.Context(self.surface)
        self.setupPixmaps(self.width, self.height)
        self.paint()

    def setupPixmaps(self, width, height):
        self.createPixmaps(width, height)
        self.combinedPattern = cairo.SurfacePattern(self.combinedSurface)

    def destroyPixmaps(self):
        self.combinedContext = None
        self.combinedSurface.finish()
        self.combinedSurface = None

        self.backgroundContext = None
        self.backgroundSurface.finish()
        self.backgroundSurface = None

        xpybutil.conn.core.FreePixmap(self.backgroundPixmapID)
        self.backgroundPixmapID = None

    def onCleanup(self):
        self.context = None
        self.surface.finish()
        self.surface = None
        self.destroyPixmaps()
        super(CairoPixmapSurface, self).onCleanup()

    def onPaint(self):
        #FIXME: Track whether or not this surface is visible, and don't repaint if it's not!
        self.context.set_source(self.combinedPattern)
        self.context.paint()

    def onResize(self, newWidth, newHeight):
        self.surface.set_size(newWidth, newHeight)
        super(CairoPixmapSurface, self).onResize(newWidth, newHeight)

    def updateForeground(self):
        self.combinedContext.set_source(self.backgroundPattern)
        self.combinedContext.paint()
        self.drawForeground(self.combinedContext)
        self.combinedSurface.flush()

        self.paint()


class CairoImageSurface(CacheableCairoSurface):
    """Cache to a Cairo image, and redraw the window using Cairo.

    """
    resizeThreshold = 20

    def onSetup(self):
        self.setupImages(self.width, self.height)

    def setupImages(self, width, height):
        self.imageWidth = width
        self.imageHeight = height

        # Set up background image.
        self.backgroundSurface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        self.backgroundContext = cairo.Context(self.backgroundSurface)
        self.setupWindowBackground(self.backgroundContext)

        self.setupBackground(self.backgroundContext)
        self.drawBackground(self.backgroundContext)
        self.backgroundSurface.flush()

        self.backgroundPattern = cairo.SurfacePattern(self.backgroundSurface)

        # Set up combined image.
        self.combinedSurface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
        self.combinedContext = cairo.Context(self.combinedSurface)
        self.setupWindowBackground(self.combinedContext)

        self.setupForeground(self.combinedContext)
        self.combinedContext.set_source(self.backgroundPattern)
        self.combinedContext.paint()
        self.drawForeground(self.combinedContext)
        self.combinedSurface.flush()

        self.combinedPattern = cairo.SurfacePattern(self.combinedSurface)

    def destroyImages(self):
        self.combinedContext = None
        self.combinedSurface.finish()
        self.combinedSurface = None

        self.backgroundContext = None
        self.backgroundSurface.finish()
        self.backgroundSurface = None

    def onCleanup(self):
        self.destroyImages()
        super(CairoImageSurface, self).onCleanup()

    def onPaint(self):
        #FIXME: Track whether or not this surface is visible, and don't repaint if it's not!
        self.context.set_source(self.combinedPattern)
        self.context.paint()

    def onResize(self, newWidth, newHeight):
        self.surface.set_size(newWidth, newHeight)

        # Don't bother resizing the images if we're within the resize threshold.
        rst = self.resizeThreshold
        if newWidth > self.imageWidth or newHeight > self.imageHeight \
                or newWidth + 2 * rst < self.imageWidth or newHeight + 2 * rst < self.imageHeight:
            self.destroyImages()
            super(CairoImageSurface, self).onResize(newWidth, newHeight)
            self.setupImages(newWidth + rst, newHeight + rst)
            self.paint()

        else:
            super(CairoImageSurface, self).onResize(newWidth, newHeight)
            self.updateBackground()

    def updateBackground(self):
        self.drawBackground(self.backgroundContext)
        self.backgroundSurface.flush()
        self.updateForeground()

    def updateForeground(self):
        self.combinedContext.set_source(self.backgroundPattern)
        self.combinedContext.paint()
        self.drawForeground(self.combinedContext)
        self.combinedSurface.flush()

        self.paint()


settings.setDefaults(
        surfaceCacheMethod=CairoPixmapSurface,
        )
