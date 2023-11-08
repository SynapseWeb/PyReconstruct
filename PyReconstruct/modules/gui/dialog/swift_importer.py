import json

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog, 
    QDialogButtonBox, 
    QLabel, 
    QVBoxLayout,
    QGridLayout,
    QComboBox
)

from PyReconstruct.modules.gui.utils import notify

def get_available_scales(project_filepath):
    """Return scales in a project file as a list of ints."""
    with open(project_filepath, "r") as fp: swift_json = json.load(fp)
    scales_data = swift_json["data"]["scales"]
    scale_names = list(scales_data.keys())
    return [int(scale.split("_")[1]) for scale in scale_names]


class SwiftDialog(QDialog):

    def __init__(self, parent, project_fp : str):
        """Create a dialog for importing transforms form SWiFT project files.
        
            Params:
                project_fp (str): filepath to a SWiFT project file.
        """
        super().__init__(parent)
        self.setWindowTitle("Import SWiFT transforms")
        
        scales_available = get_available_scales(project_fp)
        scales_available.sort()
        print(f'Available SWiFT project scales: {scales_available}')

        scale_text = QLabel(self, text="Scale")
        self.scale_input = QComboBox(self)
        items = []
        for scale in scales_available:
            items.append(str(scale))
        self.scale_input.addItems(items)

        cal_text = QLabel(self, text="Includes cal grid")
        self.cal_input = QCheckBox(self)

        layout = QGridLayout()

        r = 0
        layout.addWidget(scale_text, r, 0)
        layout.addWidget(self.scale_input, r, 1)
        r += 1

        layout.addWidget(cal_text, r, 0)
        layout.addWidget(self.cal_input, r, 1)
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

        if not self.scale_input.currentText():
            notify("Please select a scale to import.")
            return
        
        super().accept()
    
    def exec(self):
        "Run the dialog."

        confirmed = super().exec()
        
        if confirmed:

            scale = int(self.scale_input.currentText())
            cal_grid = self.cal_input.isChecked()

            response = (scale, cal_grid)
            
            return response, True
        
        else:
            
            return None, False
