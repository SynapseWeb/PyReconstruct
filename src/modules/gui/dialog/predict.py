import os

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog, 
    QDialogButtonBox, 
    QLabel, 
    QVBoxLayout,
    QGridLayout,
    QComboBox,
    QLineEdit
)
from gunpowder import downsample

from .helper import BrowseWidget

from modules.gui.utils import notify

class PredictDialog(QDialog):

    def __init__(self, parent, models : dict, opts : dict):
        """Create a dialog for predicting an autoseg model.
        
            Params:
                parent (QWidget): the parent of the dialog
                models (dict): the dictionary containing the model paths
                opts (dict): a dictionary containin autoseg options
        """
        super().__init__(parent)

        self.setWindowTitle("Predict")

        zarr_fp_text = QLabel(self, text="Zarr")
        self.zarr_fp_input = BrowseWidget(self, type="dir")

        if opts.get("zarr_current"):
            self.zarr_fp_input.le.setText(opts.get("zarr_current"))

        self.models = models
        model_text = QLabel(self, text="Model")
        self.model_input = QComboBox(self)
        items = [""]
        for g in self.models:
            for m in self.models[g]:
                items.append(f"{g} - {m}")
        self.model_input.addItems(items)

        if opts.get("model_path"):
            original_path = os.path.dirname(opts.get("model_path"))
            original_choice = os.path.basename(original_path)
            original_type = os.path.basename(os.path.dirname(original_path))
            orig = f'{original_type} - {original_choice}'
            self.model_input.setCurrentIndex(items.index(orig))

        cfile_text = QLabel(self, text="Checkpoint:")
        self.cfile_input = BrowseWidget(self, type="file")

        if opts.get("cp_path"):
            self.cfile_input.le.setText(opts.get("cp_path"))

        write_text = QLabel(self, text="Write")
        self.write_input = QComboBox(self)
        write_opts = ["affs", "lsds", "mask", "all"]
        self.write_input.addItems(write_opts)

        current_write = opts.get("write")
        if current_write:
            self.write_input.setCurrentIndex(write_opts.index(current_write))

        increase_text = QLabel(self, text="Increase")
        self.increase_input = QLineEdit(self)
        self.increase_input.setText("")

        if opts.get("increase"):
            self.increase_input.setText(opts.get("increase"))

        downsample_text = QLabel(self, text="Downsample")
        self.downsample_input = QCheckBox(self)

        if opts.get("downsample") == True:
            self.downsample_input.setChecked(True)
        
        layout = QGridLayout()

        layout.addWidget(zarr_fp_text, 0, 0)
        layout.addWidget(self.zarr_fp_input, 0, 1)

        layout.addWidget(model_text, 1, 0)
        layout.addWidget(self.model_input, 1, 1)

        layout.addWidget(cfile_text, 2, 0)
        layout.addWidget(self.cfile_input, 2, 1)

        layout.addWidget(write_text, 3, 0)
        layout.addWidget(self.write_input, 3, 1)

        layout.addWidget(downsample_text, 4, 0)
        layout.addWidget(self.downsample_input, 4, 1)

        layout.addWidget(increase_text, 5, 0)
        layout.addWidget(self.increase_input, 5, 1)

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

        increase = self.increase_input.text()
        if "None" not in increase and increase.strip() != "":
            inc = [n.strip() for n in self.increase_input.text().split(",")]
            for n in inc:
                if not n.isnumeric():
                    notify("Please enter a valid numbers for increase (e.g.: 8, 96, 96).")
                    return

        super().accept()
    
    def exec(self):
        "Run the dialog."
        confirmed = super().exec()
        
        if confirmed:
            
            group, model = self.model_input.currentText().split(" - ")
            model_path = self.models[group][model]

            zarr_fp = self.zarr_fp_input.text()
            checkpoint_fp = self.cfile_input.text()
            write_opts = self.write_input.currentText()
            downsample = self.downsample_input.isChecked()

            increase = self.increase_input.text()
            if "None" in increase or increase == "":
                increase = None
            else:
                increase = tuple([int(n.strip()) for n in increase.split(",")])

            response = [
                zarr_fp,
                model_path,
                checkpoint_fp,
                write_opts,
                increase,
                downsample
            ]

            return tuple(response), True
        
        else:
            
            return None, False
