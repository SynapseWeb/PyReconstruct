from PySide6.QtWidgets import (
    QDialog, 
    QDialogButtonBox, 
    QGridLayout,
    QLabel, 
    QLineEdit, 
    QVBoxLayout
)

from modules.gui.utils import notify

from .helper import resizeLineEdit

class BCDialog(QDialog):

    def __init__(self, parent):
        """Create a dialog for brightness/contrast."""
        super().__init__(parent)

        self.setWindowTitle("Set Brightness/Contrast")

        b_text = QLabel(self, text="Brightness (-100 - 100):")
        b_input = QLineEdit(self)
        resizeLineEdit(b_input, "000")

        c_text = QLabel(self, text="Contrast (-100 - 100):")
        c_input = QLineEdit(self)
        resizeLineEdit(c_input, "000")

        grid = QGridLayout()

        grid.addWidget(b_text, 0, 0)
        grid.addWidget(b_input, 0, 1)

        grid.addWidget(c_text, 1, 0)
        grid.addWidget(c_input, 1, 1)

        self.inputs = [b_input, c_input]

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
        for input in self.inputs:
            try:
                n = int(input.text())
            except ValueError:
                notify("Please enter a valid number.")
                return
            if not -100 <= n <= 100:
                notify("Please enter a number between -100 and 100.")
                return
        
        super().accept()
    
    def exec(self):
        "Run the dialog."
        confirmed = super().exec()
        if confirmed:
            b = int(self.inputs[0].text())
            c = int(self.inputs[1].text())
            return (b, c), True
        else:
            return None, False 