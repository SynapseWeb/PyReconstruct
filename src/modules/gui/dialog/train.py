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

class TrainDialog(QDialog):

    def __init__(self, parent, models : dict):
        """Create a dialog for training an autoseg model.
        
            Params:
                parent (QWidget): the parent of the dialog
                models (dict): the dictionary containing the model paths
        """
        super().__init__(parent)

        zarr_fp_text = QLabel(self, text="Zarr:")
        self.zarr_fp_input = BrowseWidget(self, type="dir")
        self.zarr_fp_input.le.textChanged.connect(self.updateGroups)

        self.setWindowTitle("Train Model")

        iter_text = QLabel(self, text="Iterations:")
        self.iter_input = QLineEdit(self)

        savefreq_text = QLabel(self, text="Save checkpoints every:")
        self.savefreq_input = QLineEdit(self)

        group_text = QLabel(self, text="Training group name:")
        self.group_input = QComboBox(self)
        self.group_input.addItems([""])

        self.models = models
        model_text = QLabel(self, text="Training model:")
        self.model_input = QComboBox(self)
        items = [""]
        for g in self.models:
            for m in self.models[g]:
                items.append(f"{g} - {m}")
        self.model_input.addItems(items)

        cdir_text = QLabel(self, text="Checkpoints Directory")
        self.cdir_input = BrowseWidget(self, type="dir")

        pre_cache_text = QLabel(self, text="Pre Cache:")
        self.pre_cache_input = QLineEdit(self)
        self.pre_cache_input.setText("10, 40")

        minmasked_text = QLabel(self, text="Min Masked (0-1):")
        self.minmasked_input = QLineEdit(self)
        self.minmasked_input.setText("0.5")
        
        layout = QGridLayout()

        layout.addWidget(zarr_fp_text, 0, 0)
        layout.addWidget(self.zarr_fp_input, 0, 1)

        layout.addWidget(iter_text, 1, 0)
        layout.addWidget(self.iter_input, 1, 1)

        layout.addWidget(savefreq_text, 2, 0)
        layout.addWidget(self.savefreq_input, 2, 1)

        layout.addWidget(group_text, 3, 0)
        layout.addWidget(self.group_input, 3, 1)

        layout.addWidget(model_text, 4, 0)
        layout.addWidget(self.model_input, 4, 1)

        layout.addWidget(cdir_text, 5, 0)
        layout.addWidget(self.cdir_input, 5, 1)

        layout.addWidget(pre_cache_text, 6, 0)
        layout.addWidget(self.pre_cache_input, 6, 1)

        layout.addWidget(minmasked_text, 7, 0)
        layout.addWidget(self.minmasked_input, 7, 1)

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        buttonbox = QDialogButtonBox(QBtn)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        vlayout = QVBoxLayout()
        vlayout.setSpacing(10)
        vlayout.addLayout(layout)
        vlayout.addWidget(buttonbox)

        self.setLayout(vlayout)
    
    def updateGroups(self, zarr_fp):
        """Modify the displayed groups."""
        if os.path.isdir(zarr_fp):
            groups = []
            for g in zarr.open(zarr_fp):
                if g.startswith("labels"):
                    groups.append(g)
            self.group_input.clear()
            self.group_input.addItems([""] + groups)
    
    def accept(self):
        """Overwritten from parent class."""
        if not (self.zarr_fp_input.text().endswith("zarr")):
            notify("Please select a valid zarr file.")
            return

        if not (self.iter_input.text().isnumeric()):
            notify("Please enter a valid number for iterations.")
            return
        
        if not (self.savefreq_input.text().isnumeric()):
            notify("Please enter a valid number for saving frequency.")
            return
        
        if not self.group_input.currentText():
            notify("Please select a group to use for training.")
            return
        
        if not self.model_input.currentText():
            notify("Please select a model.")
            return
        
        t = self.cdir_input.text()
        if not (t and os.path.isdir(t)):
            notify("Please select a checkpoint directory.")
            return
        
        pc = [n.strip() for n in self.pre_cache_input.text().split(",")]
        for n in pc:
            if not n.isnumeric():
                notify("Please enter a valid pair of numbers for the pre cache.")
                return
        
        try:
            n = float(self.minmasked_input.text())
            if not 0 <= n <= 1:
                notify("Please enter a number between 0 and 1 for the min masked.")
                return
        except ValueError:
            notify("Please enter a valid number for the min masked value.")
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
                int(self.iter_input.text()),
                int(self.savefreq_input.text()),
                self.group_input.currentText(),
                model_path,
                self.cdir_input.text(),
                tuple([int(n.strip()) for n in self.pre_cache_input.text().split(",")]),
                float(self.minmasked_input.text())
            ]
            return tuple(response), True
        else:
            return None, False
