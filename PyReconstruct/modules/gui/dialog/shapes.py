from PySide6.QtWidgets import (
    QWidget, 
    QDialog, 
    QDialogButtonBox, 
    QRadioButton, 
    QVBoxLayout, 
    QApplication
)

from PySide6.QtGui import (
    QPainter,
    QPen,
    QPixmap,
    QIcon,
    QPalette
)

from PySide6.QtCore import (
    QPoint,
    QSize,
    Qt
)

from PyReconstruct.modules.datatypes.series import Series
from PyReconstruct.modules.calc import centroid

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
    pts = resizeShape(points)
    r = (size-2)//2
    pts = [QPoint(round(x*r + size/2), round(size-(y*r + size/2))) for x, y in pts]

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setPen(QPen(
        QApplication.palette().color(QPalette.WindowText),  # use system black or white
        1
    ))
    painter.drawPolygon(pts)
    painter.end()

    icon = QIcon(pixmap)

    return icon

def resizeShape(points : list):
    """Modify a set of points so that they have a radius of 1 centered about the origin.
    
        Params:
            points (list): the set of points describing the shape
    """
    points = points.copy()

    # center around origin and calculate the radius
    cx, cy = centroid(points)
    max_dist = 0
    for i, (x, y) in enumerate(points):
        x, y = x-cx, y-cy
        points[i] = (x, y)
        d = (x**2 + y**2) ** (0.5)
        if d > max_dist: max_dist = d
    
    # modify radius to equal zero
    points = [(x/max_dist, y/max_dist) for x, y in points]

    return points