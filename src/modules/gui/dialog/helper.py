import os

from PySide6.QtWidgets import (
    QWidget,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QFileDialog
)
from modules.constants import fd_dir

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
        global fd_dir
        if self.type == "file":
            response = QFileDialog.getOpenFileName(
                self,
                "Find File",
                dir=fd_dir.get(),
                filter=self.filter
            )[0]
        elif self.type == "dir":
            response = QFileDialog.getExistingDirectory(
                self,
                "Find Folder",
                dir=fd_dir.get()
            )
        if response:
            self.le.setText(response)
            fd_dir.set(os.path.dirname(response))
    
    def text(self):
        """Get the displayed text."""
        return self.le.text()