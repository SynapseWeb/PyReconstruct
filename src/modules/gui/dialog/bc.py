from PySide6.QtWidgets import (
    QDialog, 
    QDialogButtonBox, 
    QHBoxLayout, 
    QLabel, 
    QLineEdit, 
    QVBoxLayout
)

class BCDialog(QDialog):

    def __init__(self, parent):
        """Create a dialog for brightness/contrast."""
        super().__init__(parent)

        self.setWindowTitle("Set Brightness/Contrast")

        self.b_row = QHBoxLayout()
        self.b_text = QLabel(self)
        self.b_text.setText("Brightness (-100 - 100):")
        self.b_input = QLineEdit(self)
        self.b_row.addWidget(self.b_text)
        self.b_row.addWidget(self.b_input)

        self.c_row = QHBoxLayout()
        self.c_text = QLabel(self)
        self.c_text.setText("Contrast (-100 - 100):")
        self.c_input = QLineEdit(self)
        self.c_row.addWidget(self.c_text)
        self.c_row.addWidget(self.c_input)

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonbox = QDialogButtonBox(QBtn)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

        self.vlayout = QVBoxLayout()
        self.vlayout.setSpacing(10)
        self.vlayout.addLayout(self.b_row)
        self.vlayout.addLayout(self.c_row)
        self.vlayout.addWidget(self.buttonbox)

        self.setLayout(self.vlayout)
    
    def exec(self):
        "Run the dialog."
        confirmed = super().exec()
        if confirmed:
            b = self.b_input.text()
            c = self.c_input.text()
            try:
                b = int(b)
                if abs(b) > 100:
                    b = None
            except ValueError:
                b = None
            try:
                c = int(c)
                if abs(c) > 100:
                    c = None
            except ValueError:
                c = None
            return (b, c), confirmed
        else:
            return (None, None), False 