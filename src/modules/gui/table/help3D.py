from PySide6.QtWidgets import QDockWidget, QTableWidgetItem, QAbstractItemView
from PySide6.QtCore import Qt

from .copy_table_widget import CopyTableWidget

class Help3DWidget(QDockWidget):

    def __init__(self):
        """Create a text widget to display 3D options"""
        super().__init__()
        self.help_desc = [
            ("Left-click", "rotate scene / select objects"),
            ("Middle-click", "pan scene"),
            ("Right-click", "zoom scene in or out"),
            ("Ctrl-click", "rotate scene"),
            None,
            ("C", "toggle scale cube"),
            ("Up/Down/Left/Right", "move scale cube in XY"),
            ("Ctrl+Up/Down", "move scale cube in Z"),
            ("Right-click scale cube", "change scale cube size"),
            None,
            ("[", "decrease opacity of selected object(s)"),
            ("]", "increase opacity of selected object(s)"),
            None,
            (".", "fly camera towards last clicked point"),
            ("I", "print info about selected object"),
            ("Shift+I", "print the RGB color under the mouse"),
            # ("Y", "show the pipeline for this object as a graph"),
            ("W/S", "toggle wireframe/surface style"),
            ("P/Shift+P", "change point size of vertices"),
            ("L", "toggle edges visibility"),
            ("X", "toggle mesh visibility"),
            ("Shift+X", "invoke a cutter widget tool"),
            ("1-3", "change mesh color"),
            # ("4", "use data array as colors, if present"),
            ("5-6", "change background color(s)"),
            ("+/-", "cycle axes style"),
            ("K", "cycle available lighting styles"),
            ("Shift+K", "cycle available shading styles"),
            ("Shift+A", "toggle anti-aliasing"),
            ("Shift+D", "toggle depth-peeling (for transparencies)"),
            ("O/Shift+O", "add/remove light to scene and rotate it"),
            ("N", "show surface mesh normals"),
            ("A", "toggle interaction to Actor Mode"),
            ("J", "toggle interaction to Joystick Mode"),
            ("Shift+U", "toggle perspective/parallel projection"),
            ("R", "reset camera position"),
            ("Shift+R", "reset camera orientation to orthogonal view"),
            ("Shift+C", "print current camera settings"),
            # ("Shift+S", "save a screenshot"),
            # ("Shift+E/Shift+F", "export 3D scene to numpy file or X3D"),
            ("Q", "return control to python script"),
            ("Esc", "abort execution and exit python kernel")
        ]

        self.setFloating(True)
        self.setAllowedAreas(Qt.NoDockWidgetArea)
        self.setWindowTitle("3D Help")
        
        # create the table
        self.createTable()

        self.resize(sum([self.table.columnWidth(i) for i in (0, 1)]), 600)

        self.closed = False
        self.show()

    def setRow(self, r : int, key_desc : tuple):
        """Set the data for a row.
        
            Params:
                r (int): the row index
                key_desc (tuple): key, description
        """
        if key_desc is not None:
            k, d = key_desc
            self.table.setItem(r, 0, QTableWidgetItem(k))
            self.table.setItem(r, 1, QTableWidgetItem(d))
    
    def createTable(self):
        """Create the table widget."""
        # establish table headers
        self.horizontal_headers = ["Key", "Description"]

        self.table = CopyTableWidget(len(self.help_desc), len(self.horizontal_headers))
        self.setWidget(self.table)

        # format table
        self.table.setShowGrid(False)  # no grid
        self.table.setAlternatingRowColors(True)  # alternate row colors
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # cannot be edited
        self.table.setHorizontalHeaderLabels(self.horizontal_headers)  # titles
        self.table.verticalHeader().hide()  # no veritcal header
        
        # fill in section data
        for r, key_desc in enumerate(self.help_desc):
            self.setRow(r, key_desc)
        
        # format the table
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

    def closeEvent(self, event):
        self.closed = True
        return super().closeEvent(event)