from PySide6.QtWidgets import (
    QWidget, 
    QDialog, 
    QDialogButtonBox, 
    QHBoxLayout, 
    QLabel, 
    QLineEdit, 
    QVBoxLayout, 
    QCheckBox
)

from .helper import resizeLineEdit

from modules.gui.utils import notify

class SmoothZtraceDialog(QDialog):

    def __init__(self, parent : QWidget):
        """Create an attribute dialog.
        
            Params:
                parent (QWidget): the parent widget
                name (string): the default name
                color (tuple): the default color
        """
        super().__init__(parent)

        self.setWindowTitle("Set Attributes")

        smooth_row = QHBoxLayout()
        smooth_text = QLabel(self, text="Smoothing factor:")
        self.smooth_input = QLineEdit(self)
        resizeLineEdit(self.smooth_input, "0000")
        self.smooth_input.setText("10")
        smooth_row.addWidget(smooth_text)
        smooth_row.addWidget(self.smooth_input)

        newztrace_row = QHBoxLayout()
        self.newztrace_input = QCheckBox("Create new ztrace")
        newztrace_row.addWidget(self.newztrace_input)

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonbox = QDialogButtonBox(QBtn)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

        self.vlayout = QVBoxLayout()
        self.vlayout.setSpacing(10)
        self.vlayout.addLayout(smooth_row)
        self.vlayout.addLayout(newztrace_row)
        self.vlayout.addWidget(self.buttonbox)

        self.setLayout(self.vlayout)
    
    def accept(self):
        """Overwritten from parent class."""
        try:
            s = int(self.smooth_input.text())
        except ValueError:
            notify("Please enter a valid number.")
            return
        
        if s < 0:
            notify("Please enter a positive number.")
            return
        
        super().accept()
    
    def exec(self):
        """Run the dialog."""
        confirmed = super().exec()
        if confirmed:
            try:
                smooth = int(self.smooth_input.text())
            except ValueError:
                return None, False
            return (smooth, self.newztrace_input.isChecked()), True
        # user pressed cancel
        else:
            return None, False