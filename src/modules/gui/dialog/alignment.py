from PySide6.QtWidgets import (
    QWidget, 
    QDialog, 
    QDialogButtonBox, 
    QHBoxLayout, 
    QLabel,
    QVBoxLayout, 
    QComboBox, 
    QPushButton, 
    QInputDialog
)

class AlignmentDialog(QDialog):

    def __init__(self, parent : QWidget, alignment_names : list):
        """Create an object group dialog.
        
            Params:
                parent (QWidget): the parent widget
                alignment_names (list): the list of alignments
        """
        super().__init__(parent)

        self.setWindowTitle("Change Alignment")

        self.align_row = QHBoxLayout()
        self.align_text = QLabel(self)
        self.align_text.setText("Alignment:")
        self.align_input = QComboBox(self)
        self.align_input.addItem("")
        self.align_input.addItems(sorted(alignment_names))
        self.align_input.resize(self.align_input.sizeHint())
        self.newalign_bttn = QPushButton(self, "new_alignment", text="New Alignment...")
        self.newalign_bttn.clicked.connect(self.newAlignment)
        self.align_row.addWidget(self.align_text)
        self.align_row.addWidget(self.align_input)
        self.align_row.addWidget(self.newalign_bttn)

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonbox = QDialogButtonBox(QBtn)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

        self.vlayout = QVBoxLayout()
        self.vlayout.setSpacing(10)
        self.vlayout.addLayout(self.align_row)
        self.vlayout.addSpacing(10)
        self.vlayout.addWidget(self.buttonbox)

        self.setLayout(self.vlayout)
    
    def newAlignment(self):
        """Add a new alignment to the list."""
        new_group_name, confirmed = QInputDialog.getText(self, "New Alignment", "New alignment name:")
        if not confirmed:
            return
        self.align_input.addItem(new_group_name)
        self.align_input.setCurrentText(new_group_name)
        self.align_input.resize(self.align_input.sizeHint())
        
    def exec(self):
        """Run the dialog."""
        confirmed = super().exec()
        text = self.align_input.currentText()
        if confirmed and text:
            return self.align_input.currentText(), True
        else:
            return "", False