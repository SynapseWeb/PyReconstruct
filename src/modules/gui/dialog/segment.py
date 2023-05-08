from PySide6.QtWidgets import (
    QDialog, 
    QDialogButtonBox, 
    QLabel, 
    QLineEdit,
    QVBoxLayout,
    QGridLayout,
)

from .helper import BrowseWidget

from modules.gui.utils import notify

class SegmentDialog(QDialog):

    def __init__(self, parent):
        """Create a dialog for running an autosegmentation.
        
            Params:
                parent (QWidget): the parent of the dialog
        """
        super().__init__(parent)

        self.setWindowTitle("Segment")

        zarr_fp_text = QLabel(self, text="Zarr:")
        self.zarr_fp_input = BrowseWidget(self, type="dir")

        thresholds_text = QLabel(self, text="Thresholds:")
        self.thresholds_input = QLineEdit(self)
        self.thresholds_input.setText("0.5")
        
        layout = QGridLayout()

        layout.addWidget(zarr_fp_text, 0, 0)
        layout.addWidget(self.zarr_fp_input, 0, 1)

        layout.addWidget(thresholds_text, 1, 0)
        layout.addWidget(self.thresholds_input, 1, 1)

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        buttonbox = QDialogButtonBox(QBtn)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        vlayout = QVBoxLayout()
        vlayout.setSpacing(10)
        vlayout.addLayout(layout)
        vlayout.addWidget(buttonbox)

        self.setLayout(vlayout)
    
    def accept(self):
        """Overwritten from parent class."""
        if not (self.zarr_fp_input.text().endswith("zarr")):
            notify("Please select a valid zarr file.")
            return
        
        threshs = self.thresholds_input.text().split(",")
        for n in threshs:
            try:
                n = float(n.strip())
                if not 0 <= n <= 1:
                    notify("Please enter a threshold number between 0 and 1.")
                    return
            except ValueError:
                notify("Please enter a valid threshold number.")
                return

        super().accept()
    
    def exec(self):
        "Run the dialog."
        confirmed = super().exec()
        if confirmed:
            response = [
                self.zarr_fp_input.text(),
                tuple([float(n.strip()) for n in self.thresholds_input.text().split(",")]),
            ]
            return tuple(response), True
        else:
            return None, False