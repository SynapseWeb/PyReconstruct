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

        self.smooth_row = QHBoxLayout()
        self.smooth_text = QLabel(self)
        self.smooth_text.setText("Smoothing factor:")
        self.smooth_input = QLineEdit(self)
        self.smooth_input.setText("10")
        self.smooth_row.addWidget(self.smooth_text)
        self.smooth_row.addWidget(self.smooth_input)

        self.newztrace_row = QHBoxLayout()
        self.newztrace_input = QCheckBox("Create new ztrace")
        self.newztrace_row.addWidget(self.newztrace_input)

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonbox = QDialogButtonBox(QBtn)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

        self.vlayout = QVBoxLayout()
        self.vlayout.setSpacing(10)
        self.vlayout.addLayout(self.smooth_row)
        self.vlayout.addLayout(self.newztrace_row)
        self.vlayout.addWidget(self.buttonbox)

        self.setLayout(self.vlayout)
    
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