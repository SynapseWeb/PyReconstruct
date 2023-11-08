from PySide6.QtWidgets import (
    QDialog, 
    QDialogButtonBox, 
    QLabel, 
    QLineEdit,
    QVBoxLayout,
    QGridLayout,
    QCheckBox,
    QComboBox
)

from .helper import BrowseWidget

from PyReconstruct.modules.gui.utils import notify

class SegmentDialog(QDialog):

    def __init__(self, parent, opts):
        """Create a dialog for running an autosegmentation.
        
            Params:
                parent (QWidget): the parent of the dialog
                opts (dict): segmentations opts
        """
        super().__init__(parent)

        self.setWindowTitle("Segment")

        zarr_fp_text = QLabel(self, text="Zarr")
        self.zarr_fp_input = BrowseWidget(self, type="dir")

        if "zarr_current" in opts:
            self.zarr_fp_input.le.setText(opts["zarr_current"])

        thresholds_text = QLabel(self, text="Thresholds")
        self.thresholds_input = QLineEdit(self)
        self.thresholds_input.setText("0.5")

        if "thresholds" in opts:
            self.thresholds_input.setText(", ".join(map(str, opts["thresholds"])))

        downsample_text = QLabel(self, text="Downsample")
        self.downsample_input = QLineEdit(self)
        self.downsample_input.setText("1")

        if "downsample_int" in opts:
            self.downsample_input.setText(str(opts["downsample_int"]))

        norm_preds_text = QLabel(self, text="Normalize preds")
        self.norm_preds_input = QCheckBox(self)

        if "norm_preds" in opts:
            self.norm_preds_input.setChecked(opts["norm_preds"])

        min_seed_text = QLabel(self, text="Min seed distance")
        self.min_seed_input = QLineEdit(self)
        self.min_seed_input.setText("10")

        if "min_seed" in opts:
            self.min_seed_input.setText(str(opts["min_seed"]))

        merge_text = QLabel(self, text="Merge function")
        self.merge_input = QComboBox(self)
        funs = ["mean",
                "hist_quant_25",
                "hist_quant_50",
                "hist_quant_75",
                "hist_quant_90"]
        self.merge_input.addItems(funs)

        if "merge_fun" in opts:
            if opts["merge_fun"] in funs:
                self.merge_input.setCurrentText(opts["merge_fun"])
        
        layout = QGridLayout()

        layout.addWidget(zarr_fp_text, 0, 0)
        layout.addWidget(self.zarr_fp_input, 0, 1)

        layout.addWidget(thresholds_text, 1, 0)
        layout.addWidget(self.thresholds_input, 1, 1)

        layout.addWidget(downsample_text, 2, 0)
        layout.addWidget(self.downsample_input, 2, 1)

        layout.addWidget(norm_preds_text, 3, 0)
        layout.addWidget(self.norm_preds_input, 3, 1)

        layout.addWidget(min_seed_text, 4, 0)
        layout.addWidget(self.min_seed_input, 4, 1)

        layout.addWidget(merge_text, 5, 0)
        layout.addWidget(self.merge_input, 5, 1)

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

        if not self.downsample_input.text().isnumeric():
            notify("Please enter a value value for downsampling.")
            return

        if not self.min_seed_input.text().isnumeric():
            notify("Please enter a value value for mininum seed distance.")
            return

        super().accept()
    
    def exec(self):
        "Run the dialog."
        confirmed = super().exec()
        
        if confirmed:

            zarr_fp = self.zarr_fp_input.text()
            thresholds = tuple([float(n.strip()) for n in self.thresholds_input.text().split(",")])
            downsample = int(self.downsample_input.text())
            norm_preds = self.norm_preds_input.isChecked()
            min_seed = int(self.min_seed_input.text())
            merge_fun = self.merge_input.currentText()

            response = [
                zarr_fp,
                thresholds,
                downsample,
                norm_preds,
                min_seed,
                merge_fun
            ]
            
            return tuple(response), True
        
        else:
            
            return None, False
