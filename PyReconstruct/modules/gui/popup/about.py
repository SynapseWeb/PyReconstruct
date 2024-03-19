from PySide6.QtWidgets import (
    QDockWidget, 
    QGridLayout,
    QLabel,
    QWidget
)
from PySide6.QtCore import Qt

class AboutWidget(QDockWidget):

    def __init__(self, parent, series):
        """Create a text widget."""
        super().__init__(parent)
        self.setFloating(True)
        self.setAllowedAreas(Qt.NoDockWidgetArea)
        self.setWindowTitle("About Series")

        self.grid = QGridLayout()

        self.add("Name:", series.name)
        self.add("Editors:", ", ".join(series.editors))
        self.add("Image folder:", series.src_dir)
        self.add("Average section thickness:", str(round(series.avg_thickness, 7)))
        self.add("Average section magnification:", str(round(series.avg_mag, 7)))

        w = QWidget(self)
        w.setLayout(self.grid)
        self.setWidget(w)
        self.show()
    
    def add(self, t1 : str, t2 : str):
        """Add a key value pair to display in the widget."""
        l1 = QLabel(self, text=t1)
        f = l1.font()
        f.setBold(True)
        l1.setFont(f)
        l2 = QLabel(self, text=t2)
        r = self.grid.rowCount()
        self.grid.addWidget(l1, r, 0)
        self.grid.addWidget(l2, r, 1)
        