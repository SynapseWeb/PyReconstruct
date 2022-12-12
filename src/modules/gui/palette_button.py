from PySide6.QtWidgets import (
    QPushButton, 
    QWidget
)
from PySide6.QtGui import (
    QPainter, 
    QPen, 
    QColor,
    QBrush
)
from PySide6.QtCore import QPoint, QRect

from modules.pyrecon.trace import Trace

from modules.gui.dialog import TraceDialog

class PaletteButton(QPushButton):

    def __init__(self, parent : QWidget, manager):
        """Create the palette button.
        
            Params:
                parent (QWidget): the parent containing the button
                manager: the mananger class for the button
        """
        super().__init__(parent)
        self.manager = manager
    
    def paintEvent(self, event):
        """Draw the trace on the button."""
        super().paintEvent(event)

        # draw the trace on the button
        painter = QPainter(self)
        painter.setPen(QPen(QColor(*self.trace.color), 1))

        w = self.width()
        h = self.height()
        radius = self.trace.getRadius()
        self.scale_factor = (min(w, h) - 1) / radius / 4
        self.origin = (w/2, h/2)

        points = [QPoint(*self._resizePoint(p)) for p in self.trace.points]
        painter.drawPolygon(points)

        # draw fill if needed
        if abs(self.trace.mode) != 11:
            painter.setBrush(QBrush(QColor(*self.trace.color)))
        if abs(self.trace.mode) == 9 or abs(self.trace.mode) == 15:
            painter.setOpacity(0.5)
        painter.drawPolygon(points)

        # highlight the button if selected
        if self.isChecked():
            painter.setPen(QPen(QColor(*self.trace.color), 8))
            painter.setBrush(QBrush())
            painter.setOpacity(0.5)
            w, h = self.width(), self.height()
            painter.drawRect(QRect(0, 0, w, h))

        painter.end()


    def setTrace(self, trace : Trace):
        """Create a palette button object.
        
            Params:
                trace (Trace): the trace that is displayed on the button
        """
        self.trace = trace
        self.update()
        
    def contextMenuEvent(self, event):
        """Executed when button is right-clicked: pulls up menu for user to edit button."""
        self.openDialog()
    
    def openDialog(self):
        """Change the attributes of a trace on the palette."""
        new_attr, confirmed = TraceDialog(
            self,
            [self.trace],
            include_radius=True
        ).exec()
        if not confirmed:
            return
        
        name, color, tags, mode, radius = new_attr
        if name:
            self.trace.name = name
        if color:
            self.trace.color = color
        if tags:
            self.trace.tags = tags
        if mode:
            self.trace.mode = mode
        if radius:
            self.trace.resize(radius)
            self.trace.centerAtOrigin()
        self.setTrace(self.trace)
        self.manager.paletteButtonChanged(self)
    
    def _resizePoint(self, point : tuple) -> tuple:
        """Resize a point by the scale factor.
        
            Params:
                point (tuple): the point to resize
        """
        x = point[0]
        y = point[1]
        x *= self.scale_factor
        y *= self.scale_factor
        y *= -1
        x += self.origin[0]
        y += self.origin[1]
        return (x, y)

