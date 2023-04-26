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
        self.left_handed = self.mainwindow.mouse_palette.left_handed
        
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
        self.bttn.clicked.connect(self.mainwindow.importAutoseg)
        self.bttn.hide()

        self.placeWidgets()
    
    def placeWidgets(self):
        """Place the widgets in the correct locations."""
        if not self.left_handed:
            lbl_x = self.mainwindow.field.x() + 10
        else:
            lbl_x = (
                self.mainwindow.field.x() + self.mainwindow.field.width() -
                (self.lbl.width() + 10) - 
                (self.cb.width() + 10) - 
                (self.bttn.width())
            )
        self.lbl.move(
            lbl_x,
            self.mainwindow.field.y() + self.mainwindow.field.height() - 40
        )
        self.cb.move(
            self.lbl.x() + self.lbl.width() + 10,
            self.lbl.y() + 2
        )
        self.bttn.move(
            self.cb.x() + self.cb.width() + 10,
            self.lbl.y()
        )

    def changeGroup(self, group_name):
        """Change the group for the overlay displayed.
        
            Params:
                group_name (str): the name of the group to change to
        """
        if group_name.startswith("segmentation"):
            self.bttn.show()
        else:
            self.bttn.hide()
        self.mainwindow.setLayerGroup(group_name)
    
    def toggleHandedness(self):
        """Toggle the position of the buttons."""
        self.left_handed = not self.left_handed
        self.placeWidgets()
        self.mainwindow.field.update()
    
    def close(self):
        """Close all widgets."""
        self.lbl.close()
        self.cb.close()
        self.bttn.close()