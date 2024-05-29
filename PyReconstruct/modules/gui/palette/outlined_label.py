# TAKEN FROM: https://stackoverflow.com/questions/64290561/qlabel-correct-positioning-for-text-outline

from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QBrush, QPen, QFontMetrics, QPainter, QPainterPath, QColor
        
class OutlinedLabel(QLabel):
    
    def __init__(self, parent):
        super().__init__(parent)
        self.w = 1 / 25
        self.mode = True
        self.setBrush(Qt.white)
        self.setPen(Qt.black)
        self.setStyleSheet("QLabel { background-color: transparent; }")
    
    def setTextColor(self, color):
        self.setBrush(QColor(*color))
    
    def setOutlineColor(self, color):
        self.setPen(QColor(*color))

    def scaledOutlineMode(self):
        return self.mode

    def setScaledOutlineMode(self, state):
        self.mode = state

    def outlineThickness(self):
        return self.w * self.font().pointSize() if self.mode else self.w

    def setOutlineThickness(self, value):
        self.w = value

    def setBrush(self, brush):
        if not isinstance(brush, QBrush):
            brush = QBrush(brush)
        self.brush = brush

    def setPen(self, pen):
        if not isinstance(pen, QPen):
            pen = QPen(pen)
        pen.setJoinStyle(Qt.RoundJoin)
        self.pen = pen

    def sizeHint(self):
        w = int(self.outlineThickness() * 2 + 1)
        return super().sizeHint() + QSize(w, w)
    
    def minimumSizeHint(self):
        w = int(self.outlineThickness() * 2 + 1)
        return super().minimumSizeHint() + QSize(w, w)
    
    def paintEvent(self, event):
        w = self.outlineThickness()
        rect = self.rect()
        metrics = QFontMetrics(self.font())
        tr = metrics.boundingRect(self.text()).adjusted(0, 0, w, w)
        if self.indent() == -1:
            if self.frameWidth():
                indent = (metrics.boundingRect('x').width() + w * 2) / 2
            else:
                indent = w
        else:
            indent = self.indent()

        if self.alignment() & Qt.AlignLeft:
            x = rect.left() + indent - min(metrics.leftBearing(self.text()[0]), 0)
        elif self.alignment() & Qt.AlignRight:
            x = rect.x() + rect.width() - indent - tr.width()
        else:
            x = (rect.width() - tr.width()) / 2
            
        if self.alignment() & Qt.AlignTop:
            y = rect.top() + indent + metrics.ascent()
        elif self.alignment() & Qt.AlignBottom:
            y = rect.y() + rect.height() - indent - metrics.descent()
        else:
            y = (rect.height() + metrics.ascent() - metrics.descent()) / 2

        path = QPainterPath()
        path.addText(x, y, self.font(), self.text())
        qp = QPainter(self)
        qp.setRenderHint(QPainter.Antialiasing)

        self.pen.setWidthF(w * 2)
        qp.strokePath(path, self.pen)
        qp.fillPath(path, self.brush)