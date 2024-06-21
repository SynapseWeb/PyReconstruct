from PySide6.QtWidgets import QDockWidget, QTableWidgetItem, QAbstractItemView, QTableWidget, QWidget
from PySide6.QtCore import Qt

class Help3DWidget(QDockWidget):

    def __init__(self):
        """Create a text widget to display 3D options"""
        super().__init__()
        self.help_desc = help_3D

        self.setFloating(True)
        self.setAllowedAreas(Qt.NoDockWidgetArea)
        self.setWindowTitle("Help")
        
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
        if key_desc is None:
            return
        elif type(key_desc) is str:
            i = QTableWidgetItem(key_desc)
            f = i.font()
            f.setBold(True)
            i.setFont(f)
            self.table.setItem(r, 0, i)
        else:
            k, d = key_desc
            self.table.setItem(r, 0, QTableWidgetItem(k))
            if type(d) is str:
                self.table.setItem(r, 1, QTableWidgetItem(d))
            elif isinstance(d, QWidget):
                self.table.setCellWidget(r, 1, d)
        self.table.setRowHeight(r, 5)
    
    def createTable(self):
        """Create the table widget."""
        # establish table headers
        self.horizontal_headers = ["Key", "Description"]

        self.table = QTableWidget(len(self.help_desc) + 1, len(self.horizontal_headers))
        self.setWidget(self.table)

        # format table
        self.table.setShowGrid(False)  # no grid
        self.table.setAlternatingRowColors(True)  # alternate row colors
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # cannot be edited
        self.table.setHorizontalHeaderLabels(self.horizontal_headers)  # titles
        self.table.verticalHeader().hide()  # no veritcal header

        # fill in data
        for r, key_desc in enumerate(self.help_desc):
            self.setRow(r, key_desc)
        
        # format the table
        self.table.resizeColumnsToContents()

    def closeEvent(self, event):
        self.closed = True
        return super().closeEvent(event)

help_3D = [
    ("Left-click", "rotate scene / select objects"),
    ("Middle-click", "pan scene"),
    ("Right-click", "zoom scene in or out"),
    ("Ctrl-click", "rotate scene / select objects"),
    ("Double-click", "move to point in 2D field"),
    None,
    ("Left/Right", "translate selected object(s) in X"),
    ("Up/Down", "translate in Y"),
    ("Ctrl+Up/Down", "translate in Z"),
    None,
    ("Shift+Left/Right", "rotate selected object(s) on X-axis around the center of mass"),
    ("Shift+Up/Down", "rotate on Y-axis"),
    ("Ctrl+Shift+Up/Down", "rotate on Z-axis"),
    None,
    ("=/-", "cycle axes style"),
    None,
    ("Ctrl+A", "select all"),
    ("Ctrl+D", "deselect all"),
    ("Ctrl+G", "select all objects in selected object's host group"),
    (" ", "A 'host group' is a group of objects that are"),
    ("", "all connected by host/inhabitant relationships."),
    None,
    ("C", "toggle scale cube"),
    ("Ctrl+Shift+H", "organize objects in the scene"),
    ("Ctrl+Shift+R", "reload the selected items"),
    None,
    ("Ctrl+E", "edit attributes of selected objects"),
    ("[", "decrease opacity of selected object(s)"),
    ("]", "increase opacity of selected object(s)"),
    None,
    ("Home", "focus scene on objects"),
    ("X, Y, Z", "align view to be along X, Y, or Z axis"),
    ("F", "Set the focal point to the selected object(s)"),
    None,
    ("Delete/Backspace", "remove the selected object(s) from the scene"),
    None,
    ("Ctrl+S", "save scene")
]