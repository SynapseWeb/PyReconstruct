from PySide6.QtWidgets import QPushButton, QMenu, QInputDialog, QColorDialog, QWidget
from PySide6.QtGui import QPainter, QPen, QColor, QIcon, QPixmap
from PySide6.QtCore import Qt

from modules.pyrecon.trace import Trace

from modules.backend.gui_functions import populateMenu

from modules.gui.dialog import PaletteTraceDialog

class PaletteButton(QPushButton):

    def __init__(self, parent : QWidget, manager):
        super().__init__(parent)
        self.manager = manager

    def setTrace(self, trace : Trace):
        """Create a palette button object.
        
            Params:
                trace (Trace): the trace that is displayed on the button
        """
        self.trace = trace
        self.pixmap = QPixmap(self.size())
        self.pixmap.fill(Qt.transparent)

        # draw the trace on the button
        w = self.size().width()
        h = self.size().height()
        self.radius = self.getTraceMaxValue()
        self.scale_factor = (min(w, h) - 1) / (self.radius * 2)
        self.origin = (w/2, h/2)
        painter = QPainter(self.pixmap)
        painter.setPen(QPen(QColor(*self.trace.color), 2))
        prev_point = self._resizePoint(trace.points[-1])
        for point in trace.points.copy():
            point = self._resizePoint(point)
            painter.drawLine(*prev_point, *point)
            prev_point = point
        painter.end()
        self.setIcon(QIcon(self.pixmap))
    
    def getTraceMaxValue(self) -> float:
        """Get the max x or y value containe in the trace points (this functions as the 'radius' of the trace).
        
            Returns:
                (float) the max value of the trace"""
        max_value = 0
        for point in self.trace.points:
            if abs(point[0]) > max_value:
                max_value = point[0]
            if abs(point[1]) > max_value:
                max_value = point[1]
        return max_value
        
    def contextMenuEvent(self, event):
        """Executed when button is right-clicked: pulls up menu for user to edit button.
        
            Params:
                event: contains user input data (location of right click)
        """
        self.openDialog()
    
    def openDialog(self):
        """Change the attributes of a trace on the palette."""
        new_attr, confirmed = PaletteTraceDialog(
            self,
            self.trace,
            self.radius
        ).exec()
        if not confirmed:
            return
        
        name, color, tags, radius = new_attr
        if name:
            self.trace.name = name
        if color:
            self.trace.color = color
        if tags:
            self.trace.tags = tags
        if radius:
            self.radius = radius
        self.setTrace(self.trace)
        self.manager.paletteButtonChanged(self)
    
    def _resizePoint(self, point):
        x = point[0]
        y = point[1]
        x *= self.scale_factor
        y *= self.scale_factor
        y *= -1
        x += self.origin[0]
        y += self.origin[1]
        return (x, y)

