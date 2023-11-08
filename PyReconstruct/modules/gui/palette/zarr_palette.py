from PySide6.QtWidgets import QWidget, QPushButton, QComboBox
from PySide6.QtGui import QFont

from .outlined_label import OutlinedLabel

class ZarrPalette():

    def __init__(self, group_names : list, mainwindow : QWidget):
        """Create the mouse dock widget object.
        
            Params:
                group_names (list): the list of group names
                mainwindow (MainWindow): the parent main window of the dock
        """
        if "raw" in group_names:
            group_names.remove("raw")
        
        self.mainwindow = mainwindow
        
        self.lbl = OutlinedLabel(self.mainwindow)
        self.lbl.setText("Zarr Groups")
        self.lbl.setFont(QFont("Courier New", 16, QFont.Bold))
        
        self.lbl.resize(self.lbl.sizeHint())
        self.lbl.show()

        self.cb = QComboBox(self.mainwindow)
        self.cb.addItem("")
        self.cb.addItems(group_names)
        self.cb.resize(self.cb.sizeHint())
        self.cb.currentTextChanged.connect(self.changeGroup)
        self.cb.show()

        self.bttn = QPushButton(self.mainwindow, text="Import Contours")
        self.bttn.resize(self.bttn.sizeHint())
        self.bttn.clicked.connect(lambda : self.mainwindow.importLabels(all=True))
        self.bttn.hide()

        self.placeWidgets()
    
    def placeWidgets(self):
        """Place the widgets in the correct locations."""
        y = (
            self.mainwindow.field.y() + self.mainwindow.field.height() - 
            (15 + self.lbl.height() + self.cb.height())
        )
        if self.bttn.isVisible():
            y -= (5 + self.bttn.height())
            widgets = (self.lbl, self.cb, self.bttn)
        else:
            widgets = (self.lbl, self.cb)

        for widget in widgets:
            x = self.mainwindow.field.x() + 10
            widget.move(x, y)
            y += 5 + widget.height()

    def changeGroup(self, group_name):
        """Change the group for the overlay displayed.
        
            Params:
                group_name (str): the name of the group to change to
        """
        if group_name.startswith("seg"):
            self.bttn.show()
        else:
            self.bttn.hide()
        self.placeWidgets()
        self.mainwindow.setLayerGroup(group_name)
    
    def close(self):
        """Close all widgets."""
        self.lbl.close()
        self.cb.close()
        self.bttn.close()