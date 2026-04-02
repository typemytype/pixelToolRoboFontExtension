import AppKit
from math import floor
import vanilla
import ezui
import os

from fontTools.misc.arrayTools import pointInRect
from fontTools.pens.pointPen import ReverseContourPointPen

from mojo.events import BaseEventTool, installTool
from mojo.roboFont import CreateCursor, version
from mojo.extensions import getExtensionDefault, setExtensionDefault, ExtensionBundle
from mojo.UI import getDefault, setDefault, preferencesChanged

from generateImages import AddPixelToolRepresentationFactory

from settings import *


AddPixelToolRepresentationFactory()

pixelBundle = ExtensionBundle("Pixel Tool")
pixelCursor = CreateCursor(pixelBundle.get("pixelCursor"), hotSpot=(1, 19))
pixelToolbarIcon = pixelBundle.get("pixelToolbarIcon")


def _roundPoint(x, y):
    return int(round(x)), int(round(y))


class GridSettingsPopoverController(ezui.WindowController):

    def build(self, tool, parent, location):
        self.editingTool = tool
        self.x, self.y = location
        content = """
        !§ Pixel Tool Settings
        
        ---
        
        * TwoColumnForm       @form
        
        > : Use Grid:
        > [X] Position        @useGridPosition
        > [X] Size            @useGridSize
        
        > : Size:             @sizeLabel
        > * HorizontalStack   @pixelSizeStack
        >> [_100_] w          @pixelWidth
        >> [_100_] h          @pixelHeight 
        
        > : Shape:
        > (X) Rectangle       @pixelShape
        > ( ) Oval
        > ( ) Component
        
        > : Base Glyph:       @baseGlyphLabel
        > [_pixel_]           @baseGlyph
        """
        descriptionData = dict(
            form=dict(
                titleColumnWidth=80,
                itemColumnWidth=140,
            ),
            pixelSizeStack=dict(
                distribution="fillEqually",
            ),
            pixelWidth=dict(
                width="fill",
                valueType="integer",
            ),
            pixelHeight=dict(
                width="fill",
                valueType="integer",
            ),
        )
        self.w = ezui.EZPopover(
            content=content,
            descriptionData=descriptionData,
            parent=parent,
            # parentAlignment="top",
            # behavior="transient",
            controller=self,
            size="auto"
        )

    def started(self):
        self.w.setItemValues(getExtensionDefault(EXT_KEY, fallback=DEFAULTS))
        self.formCallback(self.w.getItem("form"))
        self.w.open(location=(self.x - 5, self.y - 5, 10, 10))

    def formCallback(self, sender):
        settings = sender.getItemValues()
        # Gray out the pixel size settings if "Use Grid Size" or "Component" are active.
        for identifier in ["pixelWidth", "pixelHeight"]:
            states = [not self.w.getItem("useGridSize").get(), not self.w.getItem("pixelShape").get() == 2]
            self.w.getItem(identifier).enable(not False in states)
        # Gray out the base glyph text field if "Component" isn’t selected.
        self.w.getItem("baseGlyph").enable(self.w.getItem("pixelShape").get() == 2)
        # Set the text fields to grid size is desired.
        if self.w.getItem("useGridSize").get():
            self.w.getItem("pixelWidth").set(getDefault("glyphViewGridx"))
            self.w.getItem("pixelHeight").set(getDefault("glyphViewGridy"))
        setExtensionDefault(EXT_KEY, self.w.getItemValues())
        self.editingTool.setup()


class PixelTool(BaseEventTool):

    def setup(self):
        if getExtensionDefault(EXT_KEY) is None:
            print("DEFAULT IS NONE!! REsetting to defaults")
            setExtensionDefault(EXT_KEY, DEFAULTS)
        self.width = int(getExtensionDefault(EXT_KEY)["pixelWidth"])
        self.height = int(getExtensionDefault(EXT_KEY)["pixelHeight"])
        self.actionMode = ADD_ACTION_MODE
        self.drawingMode = DRAWING_MODES[getExtensionDefault(EXT_KEY)["pixelShape"]]
        self.componentName = getExtensionDefault(EXT_KEY)["baseGlyph"]
        self.useGridPos = getExtensionDefault(EXT_KEY)["useGridPosition"]
        self.useGridSize = getExtensionDefault(EXT_KEY)["useGridSize"]

    def mouseDown(self, point, offset):
        glyph = self.getGlyph()

        found = self.findObjectInGlyphForPoint(glyph, point)

        glyph.prepareUndo("%s Shapes" % self.actionMode)
        if found is not None:
            # remove contour if we found one
            self.actionMode = REMOVE_ACTION_MODE
            if self.drawingMode == "Component":
                glyph.removeComponent(found)
            else:
                glyph.removeContour(found)
        else:
            # add a square around a point
            self.actionMode = ADD_ACTION_MODE
            self.addShapeInGlyphForPoint(glyph, point)

    def _rightMouseDown(self, point, event):
        view = self.getNSView()
        point = view.window().mouseLocationOutsideOfEventStream()
        x, y = view.convertPoint_fromView_(point, None)
        GridSettingsPopoverController(self, view, (x, y))

    def mouseDragged(self, point, delta):
        glyph = self.getGlyph()
        found = self.findObjectInGlyphForPoint(glyph, point)

        if self.actionMode == REMOVE_ACTION_MODE and found is not None:
            if self.drawingMode == "Component":
                glyph.removeComponent(found)
            else:
                glyph.removeContour(found)

        elif self.actionMode == ADD_ACTION_MODE and found is None:
            self.addShapeInGlyphForPoint(glyph, point)

    def mouseUp(self, point):
        glyph = self.getGlyph()
        glyph.performUndo()
        glyph.changed()
        self.actionMode = ADD_ACTION_MODE

    def findObjectInGlyphForPoint(self, glyph, point):
        x, y = point.x, point.y
        found = None
        if self.drawingMode == "Component":
            for component in glyph.components:
                if component.baseGlyph != self.componentName:
                    continue
                if component.bounds and pointInRect((x, y), component.bounds):
                    found = component
                    break
        else:
            for contour in glyph:
                if pointInRect((x, y), contour.bounds) and contour.pointInside((x, y)):
                    found = contour
                    break
        return found

    def addShapeInGlyphForPoint(self, glyph, point):
        w, h = self.width, self.height

        if self.useGridPos:
            x = int(floor(point.x / float(w))) * w
            y = int(floor(point.y / float(h))) * h
        else:
            x = point.x - w * .5
            y = point.y - h * .5

        pen = glyph.getPointPen()
        if glyph.preferredSegmentType == "qcurve":
            pen = ReverseContourPointPen(pen)

        if self.drawingMode == "Rectangle":
            pen.beginPath()
            pen.addPoint(_roundPoint(x, y), "line")
            pen.addPoint(_roundPoint(x + w, y), "line")
            pen.addPoint(_roundPoint(x + w, y + h), "line")
            pen.addPoint(_roundPoint(x, y + h), "line")

            pen.endPath()

        elif self.drawingMode == "Oval":

            hw = w / 2.
            hh = h / 2.

            r = .55
            segmentType = glyph.preferredSegmentType
            if glyph.preferredSegmentType == "qcurve":
                r = .42

            pen.beginPath()
            pen.addPoint(_roundPoint(x + hw, y), segmentType, smooth=True)
            pen.addPoint(_roundPoint(x + hw + hw * r, y))
            pen.addPoint(_roundPoint(x + w, y + hh - hh * r))

            pen.addPoint(_roundPoint(x + w, y + hh), segmentType, smooth=True)
            pen.addPoint(_roundPoint(x + w, y + hh + hh * r))
            pen.addPoint(_roundPoint(x + hw + hw * r, y + h))

            pen.addPoint(_roundPoint(x + hw, y + h), segmentType, smooth=True)
            pen.addPoint(_roundPoint(x + hw - hw * r, y + h))
            pen.addPoint(_roundPoint(x, y + hh + hh * r))

            pen.addPoint(_roundPoint(x, y + hh), segmentType, smooth=True)
            pen.addPoint(_roundPoint(x, y + hh - hh * r))
            pen.addPoint(_roundPoint(x + hw - hw * r, y))

            pen.endPath()

        elif self.drawingMode == "Component" and self.componentName and self.componentName != glyph.name:
            pen.addComponent(self.componentName, [1, 0, 0, 1, x, y])

    def getDefaultCursor(self):
        return pixelCursor

    def getToolbarIcon(self):
        return pixelToolbarIcon

    def getToolbarTip(self):
        return "Pixel Tool"


installTool(PixelTool())
