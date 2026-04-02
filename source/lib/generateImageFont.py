import AppKit
import os
import vanilla
from defconAppKit.windows.progressWindow import ProgressWindow
try:
    from fontTools.ufoLib.glifLib import glyphNameToFileName
except ImportError:
    from robofab.glifLib import glyphNameToFileName

from mojo.roboFont import CurrentFont
from mojo.extensions import getExtensionDefault

from settings import *


class GenerateImageFont(object):

    def __init__(self):
        self.font = CurrentFont()
        if self.font is None:
            return
        doc = self.font.document()
        if doc is None:
            return
        self.window = doc.getMainWindow()
        vanilla.dialogs.getFolder(parentWindow=self.window, resultCallback=self.generate)

    def generate(self, saveDir):
        if not saveDir:
            return

        saveDir = saveDir[0]

        f = self.font.naked()

        glyphs = [g for g in f if not g.template]

        progress = ProgressWindow("Generating PNGs", tickCount=len(glyphs), parentWindow=self.window)

        gridSizeX = int(getExtensionDefault(EXT_KEY, DEFAULTS)["pixelWidth"])
        gridSizeY = int(getExtensionDefault(EXT_KEY, DEFAULTS)["pixelHeight"])

        for g in glyphs:
            if g.unicode is not None:
                fileName = "%04X" % g.unicode
            else:
                fileName = glyphNameToFileName(g.name, f)
            path = os.path.join(saveDir, "%s.png" % fileName)

            image = g.getRepresentation("com.typemytype.pixelImageFactory", gridSizeX=gridSizeX, gridSizeY=gridSizeY)
            data = image.TIFFRepresentation()
            imageRep = AppKit.NSBitmapImageRep.imageRepWithData_(data)
            pngData = imageRep.representationUsingType_properties_(AppKit.NSPNGFileType, None)
            pngData.writeToFile_atomically_(path, False)
            progress.update()
        progress.close()

GenerateImageFont()
