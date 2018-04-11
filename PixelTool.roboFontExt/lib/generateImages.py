from AppKit import *

from mojo.roboFont import version as RFVersion

from settings import *


def imageFactory(glyph, font=None, gridSize=100):
    gridSize = float(gridSize)
    if font is None:
        font = glyph.font
    bounds = glyph.bounds
    if bounds is None:
        minx = miny = maxx = maxy = 0
    else:
        minx, miny, maxx, maxy = glyph.bounds
    boundsWidth = maxx - minx
    scaledDescender = round(max(abs(miny), abs(font.info.descender)) / gridSize)
    scaledAscender = round(max(maxy, font.info.ascender, font.info.capHeight) / gridSize)
    em = scaledDescender + scaledAscender

    w = round(max(glyph.width, boundsWidth) / gridSize)
    h = round(em)

    xShift = 0
    if minx < 0:
        xShift = abs(minx) / gridSize

    image = NSImage.alloc().initWithSize_((w, h))
    image.lockFocus()

    t = NSAffineTransform.alloc().init()
    t.translateXBy_yBy_(xShift, scaledDescender)
    t.scaleBy_(1 / gridSize)
    t.concat()

    NSColor.blackColor().set()
    path = glyph.getRepresentation("defconAppKit.NSBezierPath")
    path.fill()

    image.unlockFocus()
    return image


def AddPixelToolRepresentationFactory():
    if RFVersion < "2.0":
        from defcon.objects.glyph import addRepresentationFactory
        addRepresentationFactory("com.typemytype.pixelImageFactory", imageFactory)
    else:
        from defcon import Glyph, registerRepresentationFactory
        registerRepresentationFactory(Glyph, "com.typemytype.pixelImageFactory", imageFactory)
