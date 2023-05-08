from PySide6.QtWidgets import (
    QWidget, 
    QDialog, 
    QDialogButtonBox, 
    QHBoxLayout, 
    QLabel, 
    QLineEdit, 
    QVBoxLayout, 
)

from .color_button import ColorButton

class ZtraceDialog(QDialog):

    def __init__(self, parent : QWidget, name=None, color=None):
        """Create an attribute dialog.
        
            Params:
                parent (QWidget): the parent widget
                name (string): the default name
                color (tuple): the default color
        """
        super().__init__(parent)

        self.setWindowTitle("Set Attributes")

        name_row = QHBoxLayout()
        name_text = QLabel(self, text="Name:")
        self.name_input = QLineEdit(self)
        self.name_input.setText(name)
        name_row.addWidget(name_text)
        name_row.addWidget(self.name_input)

        color_row = QHBoxLayout()
        color_text = QLabel(self, text="Color:")
        self.color_input = ColorButton(color, parent)
        color_row.addWidget(color_text)
        color_row.addWidget(self.color_input)
        color_row.addStretch()

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        buttonbox = QDialogButtonBox(QBtn)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        vlayout = QVBoxLayout()
        vlayout.setSpacing(10)
        vlayout.addLayout(name_row)
        vlayout.addLayout(color_row)
        vlayout.addWidget(buttonbox)

        self.setLayout(vlayout)
    
    def exec(self):
        """Run the dialog."""
        confirmed = super().exec()
        if confirmed:
            # name
            name = self.name_input.text()
            if name == "*" or name == "":
                name = None
            color = self.color_input.getColor()

            return (name, color), True
        # user pressed cancel
        else:
            return None, False