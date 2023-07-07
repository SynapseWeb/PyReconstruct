from PySide6.QtWidgets import (
    QWidget, 
    QDialog, 
    QDialogButtonBox, 
    QRadioButton, 
    QVBoxLayout, 
)

from PySide6.QtGui import (
    QPainter,
    QPen,
    QPixmap,
    QIcon
)

from PySide6.QtCore import (
    QPoint,
    QSize,
    Qt
)

from modules.datatypes.series import Series

class ShapesDialog(QDialog):

    def __init__(self, parent : QWidget):
        """Create an trace shape dialog.
        
            Params:
                parent (QWidget): the parent widget
        """
        super().__init__(parent)

        self.setWindowTitle("Shapes")

        vlayout = QVBoxLayout()

        self.traces = Series.getDefaultPaletteTraces()[:10]
        for trace in self.traces:
            trace.resize(1)
        self.rbs = []
        size = 30

        for trace in self.traces:
            rb = QRadioButton(self)
            rb.setIcon(shapeToIcon(trace.points, size))
            rb.setIconSize(QSize(size, size))
            self.rbs.append(rb)
            vlayout.addWidget(rb)

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        buttonbox = QDialogButtonBox(QBtn)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        vlayout.addWidget(buttonbox)

        self.setLayout(vlayout)
    
    def exec(self):
        """Run the dialog."""
        confirmed = super().exec()
        if confirmed:
            for trace, rb in zip(self.traces, self.rbs):
                if rb.isChecked():
                    return trace.points, True
        
        return None, False

def shapeToIcon(points : list, size=30):
    """Convert a trace to an icon.
    
        Params:
            points (list): the list of points describing the shape
            size (int): the side length of the icon
    """
    pts = points.copy()
    r = (size-2)//2
    pts = [QPoint(round(x*r + size/2), round(size-(y*r + size/2))) for x, y in pts]

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setPen(QPen(Qt.black, 1))
    painter.drawPolygon(pts)
    painter.end()

    icon = QIcon(pixmap)

    return icon
