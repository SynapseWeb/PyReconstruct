from PySide6.QtWidgets import (
    QWidget, 
    QDialog, 
    QDialogButtonBox,  
    QVBoxLayout, 
    QRadioButton,
)

class SmoothingDialog(QDialog):

    def __init__(self, parent : QWidget, current_smoothing : str):
        """Create an attribute dialog.
        
            Params:
                parent (QWidget): the parent widget
                alignments (list): the list of possible alignments to import
        """
        super().__init__(parent)

        self.setWindowTitle("3D Smoothing")

        vlayout = QVBoxLayout()

        smoothing_algs = ["Laplacian (most smooth)", "Humphrey (less smooth)", "None (blocky)"]

        self.rbs = []
        for s in smoothing_algs:
            rb = QRadioButton(s, self)
            self.rbs.append(rb)
            vlayout.addWidget(rb)
            if s.split()[0].lower() == current_smoothing:
                rb.setChecked(True)

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
            for rb in self.rbs:
                if rb.isChecked():
                    return rb.text().split()[0].lower(), True
        
        return None, False
