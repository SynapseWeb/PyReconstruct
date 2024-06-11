import os

from PySide6.QtWidgets import (
    QWidget,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QRadioButton,
    QLabel,
    QApplication,
)
from PySide6.QtGui import (
    QPainter,
    QPalette,
)

from .file_dialog import FileDialog

from PyReconstruct.modules.gui.utils import CompleterBox

def resizeLineEdit(le : QLineEdit, text : str):
    """Resize a line edit to fit a specific string.
    
        Params:
            le (QLineEdit): the widget to modify
            text (str): the string to resize the line edit
    """
    w = le.fontMetrics().boundingRect(text).width() + 10
    le.setFixedWidth(w)

class BrowseWidget(QWidget):

    def __init__(self, parent, type="file", default_fp="", filter=None):
        """Create the browse widget."""
        super().__init__(parent)
        self.type = type
        self.filter = filter
        self.le = QLineEdit(self, text=default_fp)
        self.bttn = QPushButton(self, text="Browse")
        self.bttn.clicked.connect(self.browse)
        layout = QHBoxLayout()
        layout.addWidget(self.le)
        layout.addWidget(self.bttn)
        self.setLayout(layout)
    
    def browse(self):
        """Change the selected folder."""
        response = None
        if self.type == "file":
            response = FileDialog.get(
                "file",
                self,
                "Find File",
                filter=self.filter
            )
        elif self.type == "dir":
            response = FileDialog.get(
                "dir",
                self,
                "Find Folder"
            )
        if response:
            self.le.setText(response)
    
    def text(self):
        """Get the displayed text."""
        return self.le.text()

class MultiInput(QWidget):

    def __init__(self, parent : QWidget, entries : list = None, combo=False, combo_items : list = [], restrict_to_opts=True):
        """Create the multi line edit widget."""
        super().__init__(parent)
        self.container = parent
        self.is_combo = combo

        # attributes only applicable to combobox
        self.combo_items = combo_items
        self.restrict_to_opts = restrict_to_opts

        vbl = QVBoxLayout()
        self.input_layout = QVBoxLayout()

        if not entries:
            entries = [""]
        
        self.inputs = []
        for entry in entries:
            if self.is_combo:
                w = CompleterBox(self, self.combo_items, allow_new=(not restrict_to_opts))
                w.setCurrentText(entry)
            else:
                w = QLineEdit(self, text=entry)
            self.input_layout.addWidget(w)
            self.inputs.append(w)
        vbl.addLayout(self.input_layout)

        # create the add/remove buttons
        ar_row = QHBoxLayout()
        ar_row.addStretch(10)
        remove = QPushButton(self, text="-")
        remove.clicked.connect(self.remove)
        ar_row.addWidget(remove)
        add = QPushButton(self, text="+")
        add.clicked.connect(self.add)
        ar_row.addWidget(add)
        vbl.addLayout(ar_row)

        self.setLayout(vbl)
    
    def add(self):
        """Add a line edit row to the field."""
        if self.is_combo:
            w = CompleterBox(self, self.combo_items)
        else:
            w = QLineEdit(self)
        self.input_layout.addWidget(w)
        self.inputs.append(w)
    
    def remove(self):
        """Remove a line edit row from the field."""
        if self.inputs:
            self.inputs.pop().deleteLater()
            self.container.adjustSize()
    
    def getEntries(self):
        """Get the strings input by the user."""
        l = []
        for w in self.inputs:
            t = w.currentText() if self.is_combo else w.text()
            if t: l.append(t)
        return l

class BorderedWidget(QWidget):

    def paintEvent(self, event):
        super().paintEvent(event)
        # draw the border manually
        painter = QPainter(self)
        painter.setPen(QApplication.palette().color(QPalette.WindowText))
        painter.drawRect(self.rect().adjusted(0, 0, -1, -1))  # Adjust the rectangle to draw inside the border
    
    def addTitle(self, title : str):
        if not isinstance(self.layout(), QVBoxLayout):
            return
        
        hlayout = QHBoxLayout()
        hlayout.addStretch()
        lbl = QLabel(self.parent(), text=title)
        f = lbl.font()
        f.setBold(True)
        lbl.setFont(f)
        hlayout.addWidget(lbl)
        hlayout.addStretch()
        l : QVBoxLayout = self.layout()
        l.insertLayout(0, hlayout)


class RadioButtonGroup(QWidget):

    def __init__(self, parent, options : list, selected_option=None, horizontal=False):
        """Create the radio button group.
        
            Params:
                parent (QWidget): the parent widget
                options (list): the list of strings for the radio buttons
                selected_option(str): the selected option
                horizontal (bool): True if buttons should be arranged horizontally
        """
        super().__init__(parent)
        if horizontal:
            layout = QHBoxLayout()
        else:
            layout = QVBoxLayout()
        
        self.bttns = []
        for opt in options:
            bttn = QRadioButton(self, text=opt)
            if opt == selected_option:
                bttn.setChecked(True)
            self.bttns.append(bttn)
            layout.addWidget(bttn)
        
        self.setLayout(layout)
    
    def getSelectedIndex(self):
        """Get the index of the selected button."""
        for i, bttn in enumerate(self.bttns):
            if bttn.isChecked():
                return i
