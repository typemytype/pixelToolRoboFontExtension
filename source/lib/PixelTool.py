import AppKit
from math import floor
import vanilla
import os

from fontTools.misc.arrayTools import pointInRect
from fontTools.pens.pointPen import ReverseContourPointPen

from mojo.events import BaseEventTool, installTool
from mojo.roboFont import CreateCursor, version
from mojo.extensions import getExtensionDefault, setExtensionDefault, ExtensionBundle
from mojo.UI import getDefault, setDefault
from lib.tools.notifications import PostNotification

from settings import *
from generateImages import AddPixelToolRepresentationFactory

AddPixelToolRepresentationFactory()

pixelBundle = ExtensionBundle("Pixel Tool")
pixelCursor = CreateCursor(pixelBundle.get("pixelCursor"), hotSpot=(1, 19))
pixelToolbarIcon = pixelBundle.get("pixelToolbarIcon")


def _roundPoint(x, y):
    return int(round(x)), int(round(y))


class GridSettingsMenu(object):

    def __init__(self, tool, event, view):
        self.tool = tool

        self.drawingChoices = [RECT_MODE, OVAL_MODE, COMPONENT_MODE]

        self.view = vanilla.Group((0, 0, 0, 0))
        nsView = self.view.getNSView()
        nsView.setFrame_(AppKit.NSMakeRect(0, 0, 185, 165))

        self.view.gridText = vanilla.TextBox((10, 12, 100, 22), "Pixel Size:")
        self.view.gridInput = vanilla.EditText((120, 10, -10, 22), self.tool.size, callback=self.gridInputCallback)

        self.view.drawingMode = vanilla.RadioGroup((10, 40, -10, 75), self.drawingChoices, isVertical=True, callback=self.drawingModeCallback)
        if self.tool.drawingMode in self.drawingChoices:
            self.view.drawingMode.set(self.drawingChoices.index(self.tool.drawingMode))

        self.view.componentName = vanilla.EditText((120, 90, -10, 22), self.tool.componentName, callback=self.drawingModeCallback)
        self.view.componentName.show(self.tool.drawingMode == COMPONENT_MODE)

        self.view.useGrid = vanilla.CheckBox((11, 125, -10, 22), "Use Grid", value=self.tool.useGrid, callback=self.drawingModeCallback)

        menu = AppKit.NSMenu.alloc().init()
        settingsItem = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_("doodle.guideView", None, "")
        settingsItem.setView_(nsView)
        menu.addItem_(settingsItem)

        AppKit.NSMenu.popUpContextMenu_withEvent_forView_(menu, event, view)

    def gridInputCallback(self, sender):
        value = sender.get()
        # must be int
        try:
            value = int(value)
        except Exception:
            value = -1

        if value <= 0:
            value = self.tool.size
            sender.set(value)
            return

        self.tool.size = value
        setExtensionDefault(GRID_DEFAULTS_KEY, value)

    def drawingModeCallback(self, sender):
        i = self.view.drawingMode.get()

        value = self.drawingChoices[i]

        self.tool.drawingMode = value
        setExtensionDefault(DRAWING_DEFAULTS_KEY, value)
        componentName = ""
        if value == COMPONENT_MODE:
            self.view.componentName.show(True)
            componentName = str(self.view.componentName.get())
        else:
            self.view.componentName.show(False)
            self.view.componentName.set("")
        self.tool.componentName = componentName
        setExtensionDefault(COMPONENT_DEFAULT_KEY, componentName)

        useGrid = self.view.useGrid.get()
        self.tool.useGrid = useGrid
        setExtensionDefault(USEGRID_DEFAULT_KEY, useGrid)


class PixelTool(BaseEventTool):

    def _get_size(self):
        return self._size

    def _set_size(self, value):
        self._size = value
        setDefault("glyphViewGridx", value)
        setDefault("glyphViewGridy", value)
        PostNotification("doodle.preferencesChanged")

    size = property(_get_size, _set_size)

    def setup(self):
        self.size = int(getExtensionDefault(GRID_DEFAULTS_KEY, 50))
        self.actionMode = ADD_ACTION_MODE
        self.drawingMode = getExtensionDefault(DRAWING_DEFAULTS_KEY, RECT_MODE)
        self.componentName = getExtensionDefault(COMPONENT_DEFAULT_KEY, "")
        self.useGrid = getExtensionDefault(USEGRID_DEFAULT_KEY, True)

    def mouseDown(self, point, offset):
        glyph = self.getGlyph()

        found = self.findObjectInGlyphForPoint(glyph, point)

        glyph.prepareUndo("%s Shapes" % self.actionMode)
        if found is not None:
            # remove contour if we found one
            self.actionMode = REMOVE_ACTION_MODE
            if self.drawingMode == COMPONENT_MODE:
                glyph.removeComponent(found)
            else:
                glyph.removeContour(found)
        else:
            # add a square around a point
            self.actionMode = ADD_ACTION_MODE
            self.addShapeInGlyphForPoint(glyph, point)

    def _rightMouseDown(self, point, event):
        GridSettingsMenu(self, event, self.getNSView())

    def mouseDragged(self, point, delta):
        glyph = self.getGlyph()
        found = self.findObjectInGlyphForPoint(glyph, point)

        if self.actionMode == REMOVE_ACTION_MODE and found is not None:
            if self.drawingMode == COMPONENT_MODE:
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
        if self.drawingMode == COMPONENT_MODE:
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
        w = h = self.size

        if self.useGrid:
            x = int(floor(point.x / float(w))) * w
            y = int(floor(point.y / float(h))) * h
        else:
            x = point.x - w * .5
            y = point.y - h * .5

        pen = glyph.getPointPen()
        if glyph.preferredSegmentType == "qcurve":
            pen = ReverseContourPointPen(pen)

        if self.drawingMode == RECT_MODE:
            pen.beginPath()
            pen.addPoint(_roundPoint(x, y), "line")
            pen.addPoint(_roundPoint(x + w, y), "line")
            pen.addPoint(_roundPoint(x + w, y + h), "line")
            pen.addPoint(_roundPoint(x, y + h), "line")

            pen.endPath()

        elif self.drawingMode == OVAL_MODE:

            hw = w / 2.
            hh = h / 2.

            r = .55
            segmentType = glyph.preferredSegmentType
            if glyph.preferredSegmentType == "qcurve":
                r = .42

            pen.beginPath()
            pen.addPoint(_roundPoint(x + hw, y), segmentType)
            pen.addPoint(_roundPoint(x + hw + hw * r, y))
            pen.addPoint(_roundPoint(x + w, y + hh - hh * r))

            pen.addPoint(_roundPoint(x + w, y + hh), segmentType)
            pen.addPoint(_roundPoint(x + w, y + hh + hh * r))
            pen.addPoint(_roundPoint(x + hw + hw * r, y + h))

            pen.addPoint(_roundPoint(x + hw, y + h), segmentType)
            pen.addPoint(_roundPoint(x + hw - hw * r, y + h))
            pen.addPoint(_roundPoint(x, y + hh + hh * r))

            pen.addPoint(_roundPoint(x, y + hh), segmentType)
            pen.addPoint(_roundPoint(x, y + hh - hh * r))
            pen.addPoint(_roundPoint(x + hw - hw * r, y))

            pen.endPath()

        elif self.drawingMode == COMPONENT_MODE and self.componentName and self.componentName != glyph.name:
            pen.addComponent(self.componentName, [1, 0, 0, 1, x, y])

    def getDefaultCursor(self):
        return pixelCursor

    def getToolbarIcon(self):
        return pixelToolbarIcon

    def getToolbarTip(self):
        return "Pixel Tool"


installTool(PixelTool())
