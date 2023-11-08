import os
import zarr

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog, 
    QDialogButtonBox, 
    QLabel, 
    QLineEdit,
    QVBoxLayout,
    QGridLayout,
    QComboBox
)

from .helper import BrowseWidget

from PyReconstruct.modules.gui.utils import notify

from PyReconstruct.modules.datatypes import Series

class TrainDialog(QDialog):

    def __init__(self, parent, series : Series, models : dict, opts : dict, retrain=False):
        """Create a dialog for training an autoseg model.
        
            Params:
                parent (QWidget): the parent of the dialog
                series (Series): the series
                models (dict): the dictionary containing the model paths
                retrain (bool): True if user is retraining (picks tag and groups by default)
                opts (dict): dictionry holding autoseg options
        """
        super().__init__(parent)
        self.setWindowTitle("Train Model")
        self.retrain = retrain

        zarr_fp_text = QLabel(self, text="Zarr")
        self.zarr_fp_input = BrowseWidget(self, type="dir")

        if "zarr_current" in opts:
            self.zarr_fp_input.le.setText(opts["zarr_current"])

        iter_text = QLabel(self, text="Iterations")
        self.iter_input = QLineEdit(self)

        if "iters" in opts:
            self.iter_input.setText(str(opts["iters"]))

        savefreq_text = QLabel(self, text="Save checkpoints every")
        self.savefreq_input = QLineEdit(self)

        if "save_every" in opts:
            self.savefreq_input.setText(str(opts["save_every"]))

        if not retrain:
            group_text = QLabel(self, text="Training object group name")
            self.group_input = QComboBox(self)
            group_items = [""] + series.object_groups.getGroupList()
            self.group_input.addItems(group_items)

            if "group" in opts:
                current_group = opts["group"]
                if current_group in group_items:
                    self.group_input.setCurrentText(current_group)

        self.models = models
        model_text = QLabel(self, text="Training model")
        self.model_input = QComboBox(self)
        items = [""]
        for g in self.models:
            for m in self.models[g]:
                items.append(f"{g} - {m}")
        self.model_input.addItems(items)

        if "model_path" in opts:
            original_path = os.path.dirname(opts["model_path"])
            original_choice = os.path.basename(original_path)
            original_type = os.path.basename(os.path.dirname(original_path))
            orig = f'{original_type} - {original_choice}'
            if orig in items:
                self.model_input.setCurrentText(orig)

        cdir_text = QLabel(self, text="Checkpoints Directory")
        self.cdir_input = BrowseWidget(self, type="dir")

        if "checkpts_dir" in opts:
            self.cdir_input.le.setText(opts["checkpts_dir"])

        pre_cache_text = QLabel(self, text="Pre Cache")
        self.pre_cache_input = QLineEdit(self)
        self.pre_cache_input.setText("10, 40")

        if "pre_cache" in opts:
            pc = opts["pre_cache"]
            t = f"{pc[0]}, {pc[1]}"
            self.pre_cache_input.setText(t)

        minmasked_text = QLabel(self, text="Min Masked (0-1)")
        self.minmasked_input = QLineEdit(self)
        self.minmasked_input.setText("0.05")

        if "min_masked" in opts:
            self.minmasked_input.setText(str(opts["min_masked"]))
            
        downsample_text = QLabel(self, text="Downsample")
        self.downsample_input = QCheckBox(self)

        if "downsample_bool" in opts:
            self.downsample_input.setChecked(opts["downsample_bool"])
        
        layout = QGridLayout()

        r = 0

        layout.addWidget(zarr_fp_text, r, 0)
        layout.addWidget(self.zarr_fp_input, r, 1)
        r += 1

        layout.addWidget(iter_text, r, 0)
        layout.addWidget(self.iter_input, r, 1)
        r += 1

        layout.addWidget(savefreq_text, r, 0)
        layout.addWidget(self.savefreq_input, r, 1)
        r += 1

        if not retrain:
            layout.addWidget(group_text, r, 0)
            layout.addWidget(self.group_input, r, 1)
            r += 1

        layout.addWidget(model_text, r, 0)
        layout.addWidget(self.model_input, r, 1)
        r += 1

        layout.addWidget(cdir_text, r, 0)
        layout.addWidget(self.cdir_input, r, 1)
        r += 1

        layout.addWidget(pre_cache_text, r, 0)
        layout.addWidget(self.pre_cache_input, r, 1)
        r += 1

        layout.addWidget(minmasked_text, r, 0)
        layout.addWidget(self.minmasked_input, r, 1)
        r += 1

        layout.addWidget(downsample_text, r, 0)
        layout.addWidget(self.downsample_input, r, 1)
        r += 1

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

        if not (self.iter_input.text().isnumeric()):
            notify("Please enter a valid number for iterations.")
            return
        
        if not (self.savefreq_input.text().isnumeric()):
            notify("Please enter a valid number for saving frequency.")
            return
        
        if not self.retrain and not self.group_input.currentText():
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

            zarr_dir = self.zarr_fp_input.text()
            iterations = int(self.iter_input.text())
            save_freq = int(self.savefreq_input.text())
            groups = None if self.retrain else self.group_input.currentText()
            checkpoints_dir = self.cdir_input.text()
            pre_cache = tuple([int(n.strip()) for n in self.pre_cache_input.text().split(",")])
            minmask = float(self.minmasked_input.text())
            downsample = self.downsample_input.isChecked()

            response = [
                
                zarr_dir,
                iterations,
                save_freq,
                groups,
                model_path,
                checkpoints_dir,
                pre_cache,
                minmask,
                downsample
                
            ]
                
            return tuple(response), True
        
        else:
            
            return None, False
