from PySide6.QtWidgets import QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout

from modules.gui.colorbutton import ColorButton

class AttributeDialog(QDialog):

    def __init__(self, parent=None, name="", color=None):
        super().__init__(parent)

        self.setWindowTitle("Set Attributes")

        self.name_row = QHBoxLayout()
        self.name_text = QLabel(self)
        self.name_text.setText("Name:")
        self.name_input = QLineEdit(self)
        self.name_input.setText(name)
        self.name_row.addWidget(self.name_text)
        self.name_row.addWidget(self.name_input)

        self.color_row = QHBoxLayout()
        self.color_text = QLabel(self)
        self.color_text.setText("Color:")
        self.color_input = ColorButton(color, parent)
        self.color_row.addWidget(self.color_text)
        self.color_row.addWidget(self.color_input)
        self.color_row.addStretch()

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonbox = QDialogButtonBox(QBtn)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

        self.vlayout = QVBoxLayout()
        self.vlayout.setSpacing(10)
        self.vlayout.addLayout(self.name_row)
        self.vlayout.addLayout(self.color_row)
        self.vlayout.addWidget(self.buttonbox)

        self.setLayout(self.vlayout)
    
    def exec_(self):
        confirmed = super().exec_()
        if confirmed:
            return self.name_input.text(), self.color_input.getColor()
        else:
            return None





            