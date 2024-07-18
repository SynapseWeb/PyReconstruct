from pathlib import Path

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

        jser_loc = Path(series.filepath).parents[1] / f"{series.name}.jser"

        self.add("Filename:", f"{series.name}.jser")
        self.add("Path:", str(jser_loc.absolute()))
        self.add("Series code:", series.code)
        self.add("Editors:", ", ".join(series.editors))
        self.add("Image folder:", series.src_dir)
        self.add("Section thickness (μm):", str(round(series.avg_thickness, 4)))
        self.add("Section magnification (μm/pixel):", str(round(series.avg_mag, 4)))

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
        
