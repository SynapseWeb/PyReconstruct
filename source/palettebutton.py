from PySide2.QtWidgets import QPushButton, QMenu, QInputDialog, QColorDialog
from PySide2.QtGui import QPainter, QPen, QColor, QIcon, QPixmap
from PySide2.QtCore import Qt

from trace import Trace

class PaletteButton(QPushButton):

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
        max_value = self.getTraceMaxValue()
        self.scale_factor = (min(w, h) - 1) / (max_value * 2)
        self.origin = (w/2, h/2)
        painter = QPainter(self.pixmap)
        painter.setPen(QPen(QColor(*self.trace.color), 1))
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
        menu = QMenu(self)
        name_act = menu.addAction("Edit name...")
        name_act.triggered.connect(self.editName)
        color_act = menu.addAction("Edit color...")
        color_act.triggered.connect(self.editColor)
        size_act = menu.addAction("Edit stamp size...")
        size_act.triggered.connect(self.editSize)
        menu.exec_(event.globalPos())
    
    def editName(self):
        """Change the name of the trace on the palette."""
        text, ok = QInputDialog.getText(self, "Edit Trace Name", "Enter new trace name:", text=self.trace.name)
        if ok:
            self.trace.name = text
            self.setTrace(self.trace)
        self.parent().paletteButtonChanged(self)
        
    def editColor(self):
        """Change the color of the trace on the palette."""
        color = QColorDialog.getColor()
        if color.isValid():
            self.trace.color = (color.red(), color.green(), color.blue())
            self.setTrace(self.trace)
        self.parent().paletteButtonChanged(self)
    
    def editSize(self):
        """Change the radius of the trace on the palette."""
        prev_radius = self.getTraceMaxValue()
        new_radius, ok = QInputDialog.getDouble(self, "Edit Stamp Size", "Enter stamp radius:", value=prev_radius, minValue=0, decimals=4)
        if ok:
            if new_radius == 0:
                return
            scale_factor = new_radius / prev_radius
            for i in range(len(self.trace.points)):
                point = self.trace.points[i]
                x = point[0] * scale_factor
                y = point[1] * scale_factor
                self.trace.points[i] = (x, y)
            self.setTrace(self.trace)
        self.parent().paletteButtonChanged(self)
    
    def _resizePoint(self, point):
        x = point[0]
        y = point[1]
        x *= self.scale_factor
        y *= self.scale_factor
        y *= -1
        x += self.origin[0]
        y += self.origin[1]
        return (x, y)

