from PySide6.QtWidgets import QDockWidget, QTableWidgetItem, QAbstractItemView, QLabel, QWidget
from PySide6.QtCore import Qt

from .copy_table_widget import CopyTableWidget

class HelpWidget(QDockWidget):

    def __init__(self, mode):
        """Create a text widget to display 3D options"""
        super().__init__()
        self.mode = mode
        if self.mode == "3D":
            self.help_desc = help_3D
        elif self.mode == "shortcuts":
            self.help_desc = help_shortcuts

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

        self.table = CopyTableWidget(len(self.help_desc) + 1, len(self.horizontal_headers))
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
    ("Ctrl-click", "rotate scene"),
    ("Double-click", "move to point in 2D field"),
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

link = "https://wikis.utexas.edu/display/khlab/PyReconstruct+user+guide"
link_lbl = QLabel()
link_lbl.setOpenExternalLinks(True)
link_lbl.setText(f'<a href="{link}">{link}</a>')
help_shortcuts = [
    ("Full wiki:", link_lbl),
    None,
    "General",
    ('Delete/Backspace', 'Delete selected traces'),
    ('', 'Remove last entered point when polyline tracing or using scissors.'),
    ('', 'Delete selected entry when using the lists'),
    ('? (Shift-/)', 'Display keyboard shortcuts'),
    ('Page Up', 'Display the next (higher) section'),
    ('Page Down', 'Display the preceding (lower) section'),
    ('/ ', 'Switch back & forth between the current section and last section viewed'),
    None,
    "View",
    ('H', 'Toggle hide all traces, regardless of individual trace hide status'),
    ('A', 'Toggle show all traces, regardless of individual trace hide status'),
    ('I', 'Toggle hide section image'),
    ('-', 'Decrease brightness'),
    ('=', 'Increase brightness'),
    ('[', 'Decrease contrast'),
    (']', 'Increase contrast'),
    ('Space', 'Blend the current section with the last section viewed'),
    ('Home', 'Set the view to the image'),
    None,
    "Field Interactions",
    ('Ctrl-A', 'Select all traces on a section'),
    ('Ctrl-D', 'Deselect all traces on section'),
    ('Ctrl-E', 'Edit the attributes of the selected trace(s)'),
    ('Ctrl-M', 'Merge the selected traces'),
    ('Ctrl-Shift-M', 'Merge the attributes of the selected traces'),
    ('Ctrl-H', 'Hide the selected traces'),
    ('Ctrl-U', 'Unhide all hidden traces on the current section'),
    ('Shift-G', 'Modify the current palette button to match attributes of first selected trace'),
    ('Ctrl-Shift-G', 'Modiy the current palette button to match attributes AND shape of first selected trace'),
    ('Ctrl-Shift-U', 'Unlock the current section'),
    ('Ctrl-T', 'Modify the transform on current section'),
    None,
    "Edit",
    ('Ctrl-Z', 'Undo'),
    ('Ctrl-Y', 'Re-do'),
    ('Ctrl-C', 'Copy the selected traces onto the clipboard'),
    ('Ctrl-X', 'Cut selected traces onto the clipboard'),
    ('Ctrl-V', 'Paste clipboard traces into section'),
    ('Ctrl-B', 'Paste attributes of clipboard traces onto selected traces'),
    None,
    "Navigate",
    ('Ctrl-F', 'Find the first instance of a trace in series'),
    ('Ctrl-Shift-F', 'Find a trace on the current section'),
    ('Ctrl-G', 'Go to a specific section number'),
    None,
    "File",
    ('Ctrl-O', 'Open a series file'),
    ('Ctrl-S', 'Save'),
    ('Ctrl-Shift-B', 'Backup series'),
    ('Ctrl-N', 'New'),
    ('Ctrl-R', 'Restart'),
    ('Ctrl-Q', 'Quit'),
    None,
    "Lists",
    ('Ctrl-Shift-O', 'Open the Object List'),
    ('Ctrl-Shift-C', 'Toggle curation columns in object list'),
    ('Ctrl-Shift-T', 'Open the Trace List'),
    ('Ctrl-Shift-Z', 'Open the Ztrace List'),
    ('Ctrl-Shift-S', 'Open the Section List'),
    ('Ctrl-Shift-A', 'Switch/modify alignments'),
    None,
    "Trace Palette",
    ('#, Shift-#', 'Select a trace on the palette'),
    ('Ctrl-#, Ctrl-Shift-#', 'Edit attributes for a single trace on the palette'),
    ('Ctrl-Shift-P', 'Switch/modify palettes'),
    None,
    "Arrow Keys",
    ('Left/Right/Up/Down', 'Translate selected traces or image if no trace selected'),
    ('Ctrl-Left/Right/Up/Down', 'Translate traces or image a small amount'),
    ('Shift-Left/Right/Up/Down', 'Translate trace or image a large amount'),
    ('Ctrl-Shift-Left/Right/Up/Down', 'Rotate the image around the mouse'),
    None,
    "Tool Palette",
    ('P', 'Use the pointer tool'),
    ('Z', 'Use the pan/zoom tool'),
    ('K', 'Use the knife tool'),
    ('C', 'Use the closed trace tool'),
    ('O', 'Use the open trace tool'),
    ('S', 'Use the stamp tool'),
    ('F', 'Use the flag tool'),
    None,
    "3D Scene Shortcuts:",
    None,
    ("Shift-/", "Pull up shortcuts for 3D scene"),
    None,
] + help_3D