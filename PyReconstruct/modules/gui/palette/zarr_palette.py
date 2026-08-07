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

        # "Shuffle colors" reshuffles the preview colors; a one-line caption
        # states plainly what the button does and that the import keeps what
        # the preview shows. Both are shown only for segmentation groups (see
        # changeGroup), alongside "Import Contours".
        self.shuffle_bttn = QPushButton(self.mainwindow, text="Shuffle colors")
        self.shuffle_bttn.resize(self.shuffle_bttn.sizeHint())
        self.shuffle_bttn.clicked.connect(self.mainwindow.shuffleAutosegColors)
        self.shuffle_bttn.hide()

        self.caption = OutlinedLabel(self.mainwindow)
        self.caption.setText("Shuffle recolors the preview; import keeps what you see.")
        self.caption.setFont(QFont("Courier New", 10))
        self.caption.resize(self.caption.sizeHint())
        self.caption.hide()

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
            y -= (5 + self.caption.height() + 5 + self.shuffle_bttn.height()
                  + 5 + self.bttn.height())
            widgets = (self.lbl, self.cb, self.caption, self.shuffle_bttn, self.bttn)
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
        show = group_name.startswith("seg")
        for w in (self.bttn, self.shuffle_bttn, self.caption):
            w.setVisible(show)
        self.placeWidgets()
        self.mainwindow.setLayerGroup(group_name)

    def close(self):
        """Close all widgets."""
        self.lbl.close()
        self.cb.close()
        self.caption.close()
        self.shuffle_bttn.close()
        self.bttn.close()