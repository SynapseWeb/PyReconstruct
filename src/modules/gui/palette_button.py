from PySide6.QtWidgets import QPushButton, QMenu, QInputDialog, QColorDialog, QWidget
from PySide6.QtGui import QPainter, QPen, QColor, QIcon, QPixmap
from PySide6.QtCore import Qt, QPoint

from modules.pyrecon.trace import Trace

from modules.gui.gui_functions import populateMenu

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
        radius = self.trace.getRadius()
        self.scale_factor = (min(w, h) - 1) / radius / 2
        self.origin = (w/2, h/2)

        painter = QPainter(self.pixmap)
        painter.setPen(QPen(QColor(*self.trace.color), 2))
        points = [QPoint(*self._resizePoint(p)) for p in trace.points]
        painter.drawPolygon(points)
        painter.end()

        self.setIcon(QIcon(self.pixmap))
        
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
            self.trace.resize(radius)
            self.trace.centerAtOrigin()
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

