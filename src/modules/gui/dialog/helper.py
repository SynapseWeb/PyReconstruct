from PySide6.QtWidgets import (
    QWidget,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QFileDialog
)

def resizeLineEdit(le : QLineEdit, text : str):
    """Resize a line edit to fit a specific string.
    
        Params:
            le (QLineEdit): the widget to modify
            text (str): the string to resize the line edit
    """
    w = le.fontMetrics().boundingRect(text).width() + 10
    le.setFixedWidth(w)

class BrowseWidget(QWidget):

    def __init__(self, parent, type="file"):
        """Create the browse widget."""
        super().__init__(parent)
        self.type = type
        self.le = QLineEdit(self)
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
            response = QFileDialog.getOpenFileName(
                self,
                "Find File"
            )[0]
        elif self.type == "dir":
            response = QFileDialog.getExistingDirectory(
                self,
                "Find Folder"
            )
        if response:
            self.le.setText(response)
    
    def text(self):
        """Get the displayed text."""
        return self.le.text()