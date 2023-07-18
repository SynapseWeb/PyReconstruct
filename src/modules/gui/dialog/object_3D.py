from PySide6.QtWidgets import (
    QDialog, 
    QDialogButtonBox, 
    QLabel, 
    QLineEdit, 
    QVBoxLayout, 
    QGridLayout,
    QComboBox
)

from modules.gui.utils import notify

from .helper import resizeLineEdit

class Object3DDialog(QDialog):

    def __init__(self, parent, type3D=None, opacity=None):
        """Create a dialog for 3D object settings."""
        super().__init__(parent)

        self.setWindowTitle("3D Object Settings")

        type_text = QLabel(self, text="3D Type:")
        self.type_input = QComboBox(self)
        type_list = ["surface", "spheres", "contours"]
        if not type3D:
            self.type_input.addItem("")
        self.type_input.addItems(type_list)
        if type3D:
            self.type_input.setCurrentText(type3D)
        self.type_input.resize(self.type_input.sizeHint())

        opacity_text = QLabel(self, text="Opacity (0-1):")
        self.opacity_input = QLineEdit(self)
        resizeLineEdit(self.opacity_input, "0.000")
        if opacity:
            self.opacity_input.setText(str(round(opacity, 6)))

        grid = QGridLayout()

        grid.addWidget(type_text, 0, 0)
        grid.addWidget(self.type_input, 0, 1)

        grid.addWidget(opacity_text, 1, 0)
        grid.addWidget(self.opacity_input, 1, 1)

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        buttonbox = QDialogButtonBox(QBtn)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        vlayout = QVBoxLayout()
        vlayout.setSpacing(10)
        vlayout.addLayout(grid)
        vlayout.addWidget(buttonbox)

        self.setLayout(vlayout)
    
    def accept(self):
        """Overwritten from parent class."""
        try:
            o = float(self.opacity_input.text())
        except ValueError:
            notify("Please enter a valid number.")
            return
        
        if not 0 <= o <= 1:
            notify("Please enter a number between 0 and 1.")
            return
        
        super().accept()
    
    def exec(self):
        "Run the dialog."
        confirmed = super().exec()
        if confirmed:
            type3D = self.type_input.currentText()
            opacity = float(self.opacity_input.text())
            return (type3D, opacity), True
        else:
            return None, None