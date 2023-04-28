import os
import zarr

from PySide6.QtWidgets import (
    QDialog, 
    QDialogButtonBox, 
    QLabel, 
    QLineEdit,
    QVBoxLayout,
    QGridLayout,
    QComboBox
)

from .helper import BrowseWidget

from modules.gui.utils import notify

class SegmentDialog(QDialog):

    def __init__(self, parent, models : dict):
        """Create a dialog for training an autoseg model.
        
            Params:
                parent (QWidget): the parent of the dialog
                models (dict): the dictionary containing the model paths
        """
        super().__init__(parent)

        self.setWindowTitle("Segment")

        zarr_fp_text = QLabel(self, text="Zarr:")
        self.zarr_fp_input = BrowseWidget(self, type="dir")

        self.models = models
        model_text = QLabel(self, text="Model:")
        self.model_input = QComboBox(self)
        items = [""]
        for g in self.models:
            for m in self.models[g]:
                items.append(f"{g} - {m}")
        self.model_input.addItems(items)

        cfile_text = QLabel(self, text="Checkpoint:")
        self.cfile_input = BrowseWidget(self, type="file")

        thresholds_text = QLabel(self, text="Thresholds:")
        self.thresholds_input = QLineEdit(self)
        self.thresholds_input.setText("0.5")
        
        layout = QGridLayout()

        layout.addWidget(zarr_fp_text, 0, 0)
        layout.addWidget(self.zarr_fp_input, 0, 1)

        layout.addWidget(model_text, 1, 0)
        layout.addWidget(self.model_input, 1, 1)

        layout.addWidget(cfile_text, 2, 0)
        layout.addWidget(self.cfile_input, 2, 1)

        layout.addWidget(thresholds_text, 3, 0)
        layout.addWidget(self.thresholds_input, 3, 1)

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
        
        if not self.model_input.currentText():
            notify("Please select a model.")
            return
        
        t = self.cfile_input.text()
        if not (t and os.path.isfile(t)):
            notify("Please select a checkpoint file.")
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
            group, model = self.model_input.currentText().split(" - ")
            model_path = self.models[group][model] 

            response = [
                self.zarr_fp_input.text(),
                model_path,
                self.cfile_input.text(),
                tuple([float(n.strip()) for n in self.thresholds_input.text().split(",")]),
            ]
            return tuple(response), True
        else:
            return None, False