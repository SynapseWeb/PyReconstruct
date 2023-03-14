from PySide6.QtWidgets import (
    QDialog, 
    QDialogButtonBox, 
    QHBoxLayout, 
    QLabel, 
    QLineEdit, 
    QVBoxLayout, 
    QComboBox
)

class Object3DDialog(QDialog):

    def __init__(self, parent, type3D=None, opacity=None):
        """Create a dialog for 3D object settings."""
        super().__init__(parent)

        self.setWindowTitle("3D Object Settings")

        self.type_row = QHBoxLayout()
        self.type_text = QLabel(self)
        self.type_text.setText("3D Type:")
        self.type_input = QComboBox(self)
        type_list = ["surface", "spheres"]
        if not type3D:
            self.type_input.addItem("")
        self.type_input.addItems(type_list)
        if type3D:
            self.type_input.setCurrentText(type3D)
        self.type_input.resize(self.type_input.sizeHint())
        self.type_row.addWidget(self.type_text)
        self.type_row.addWidget(self.type_input)

        self.opacity_row = QHBoxLayout()
        self.opacity_text = QLabel(self)
        self.opacity_text.setText("Opacity (0-1):")
        self.opacity_input = QLineEdit(self)
        if opacity:
            self.opacity_input.setText(str(round(opacity, 6)))
        self.opacity_row.addWidget(self.opacity_text)
        self.opacity_row.addWidget(self.opacity_input)

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonbox = QDialogButtonBox(QBtn)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

        self.vlayout = QVBoxLayout()
        self.vlayout.setSpacing(10)
        self.vlayout.addLayout(self.type_row)
        self.vlayout.addLayout(self.opacity_row)
        self.vlayout.addWidget(self.buttonbox)

        self.setLayout(self.vlayout)
    
    def exec(self):
        "Run the dialog."
        confirmed = super().exec()
        if confirmed:
            type3D = self.type_input.currentText()
            opacity = self.opacity_input.text()
            try:
                opacity = float(opacity)
            except ValueError:
                opacity = None
            return (type3D, opacity), confirmed
        else:
            return None, None