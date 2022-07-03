from PySide2.QtWidgets import QPushButton
from PySide2.QtGui import QPainter, QPen, QColor, QIcon, QPixmap
from PySide2.QtCore import Qt

class PaletteButton(QPushButton):

    def setTrace(self, trace):
        self.trace = trace
        self.pixmap = QPixmap(self.size())
        self.pixmap.fill(Qt.transparent)

        # draw the trace on the pixmap
        w = self.size().width()
        h = self.size().height()
        self.scale_factor = min(w, h) - 1
        self.origin = (w/2, h/2)

        painter = QPainter(self.pixmap)
        painter.setPen(QPen(QColor(*self.trace.color), 1))
        prev_point = self._translatePoint(trace.points[-1])
        for point in trace.points.copy():
            point = self._translatePoint(point)
            painter.drawLine(*prev_point, *point)
            prev_point = point
        painter.end()

        self.setIcon(QIcon(self.pixmap))
    
    def _translatePoint(self, point):
        x = point[0]
        y = point[1]
        x *= self.scale_factor
        y *= self.scale_factor
        y *= -1
        x += self.origin[0]
        y += self.origin[1]
        return (x, y)

