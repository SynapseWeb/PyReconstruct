from PySide6.QtWidgets import (
    QWidget, 
    QDialog, 
    QDialogButtonBox, 
    QCheckBox, 
    QVBoxLayout, 
    QCheckBox,
)

class ImportTransformsDialog(QDialog):

    def __init__(self, parent : QWidget, alignments : list):
        """Create an attribute dialog.
        
            Params:
                parent (QWidget): the parent widget
                alignments (list): the list of possible alignments to import
        """
        super().__init__(parent)

        self.setWindowTitle("Set Attributes")

        vlayout = QVBoxLayout()

        self.cbs = []
        for a in alignments:
            cb = QCheckBox(a, self)
            self.cbs.append(cb)
            vlayout.addWidget(cb)

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        buttonbox = QDialogButtonBox(QBtn)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        vlayout.addWidget(buttonbox)

        self.setLayout(vlayout)
    
    def exec(self):
        """Run the dialog."""
        confirmed = super().exec()
        if confirmed:
            alignments = []
            for cb in self.cbs:
                if cb.isChecked():
                    alignments.append(cb.text())
            return alignments, True
        
        # user pressed cancel
        else:
            return None, False
