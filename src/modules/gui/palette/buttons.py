import time

from PySide6.QtWidgets import (
    QPushButton
)
from PySide6.QtGui import (
    QPainter, 
    QPen, 
    QColor,
    QBrush
)
from PySide6.QtCore import QPoint, QRect

from modules.datatypes import Trace
from modules.gui.dialog import TraceDialog

class MoveableButton(QPushButton):

    def __init__(self, parent, manager, group_name):
        """Create the mode button."""
        super().__init__(parent)
        self.manager = manager
        self.group_name = group_name
        self.click_time = None
        self.clicked_x = None
        self.clicked_y = None
    
    def mousePressEvent(self, event):
        """Called when button is pressed."""
        self.click_time = time.time()
        self.clicked_x = event.globalX()
        self.clicked_y = event.globalY()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        """Called when button is moved."""
        if time.time() - self.click_time < self.manager.mainwindow.field.max_click_time:
            return
        self.manager.is_dragging = True
        diff_x = event.globalX() - self.clicked_x
        diff_y = event.globalY() - self.clicked_y
        self.manager.moveButton(diff_x, diff_y, self.group_name)
        self.clicked_x = event.globalX()
        self.clicked_y = event.globalY()
        self.manager.resize()
    
    def mouseReleaseEvent(self, event):
        """Called when mouse is released."""
        super().mouseReleaseEvent(event)
        self.manager.is_dragging = False


class ModeButton(MoveableButton):

    def __init__(self, parent, manager):
        super().__init__(parent, manager, "mode")

    def paintEvent(self, event):
        """Add a highlighting border to selected buttons."""
        super().paintEvent(event)
        if self.isChecked():
            painter = QPainter(self)
            painter.setPen(QPen(QColor(255, 255, 0), 2))
            painter.setOpacity(1)
            w, h = self.width(), self.height()
            painter.drawRect(QRect(0, 0, w, h))


class PaletteButton(MoveableButton):

    def __init__(self, parent, manager):
        super().__init__(parent, manager, "trace")
    
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
        if self.trace.fill_mode[0] != "none":
            painter.setBrush(QBrush(QColor(*self.trace.color)))
        if self.trace.fill_mode[0] == "transparent":
            painter.setOpacity(0.3)
        painter.drawPolygon(points)

        # highlight the button if selected
        if self.isChecked():
            painter.setPen(QPen(QColor(255, 255, 0), 2))
            painter.setBrush(QBrush())
            painter.setOpacity(1)
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
        t, confirmed = TraceDialog(
            self,
            [self.trace],
            is_palette=True
        ).exec()
        if not confirmed:
            return
        
        name, color, points, tags, mode, radius = (
            t.name, t.color, t.points, t.tags, t.fill_mode, t.getRadius()
        )
        if name:
            self.trace.name = name
        if color:
            self.trace.color = color
        if points:
            original_radius = self.trace.getRadius()
            self.trace.points = points
            self.trace.resize(original_radius)
        if tags:
            self.trace.tags = tags
        fill_mode = list(self.trace.fill_mode)
        style, condition = mode
        if style:
            fill_mode[0] = style
        if condition:
            fill_mode[1] = condition
        self.trace.fill_mode = tuple(fill_mode)
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