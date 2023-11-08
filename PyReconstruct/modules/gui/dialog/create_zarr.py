from PySide6.QtWidgets import (
    QWidget, 
    QDialog, 
    QDialogButtonBox, 
    QHBoxLayout, 
    QLabel, 
    QLineEdit,
    QVBoxLayout, 
    QComboBox, 
    QPushButton
)

from .helper import resizeLineEdit

from PyReconstruct.modules.datatypes import Series
from PyReconstruct.modules.gui.utils import notify

class CreateZarrDialog(QDialog):

    def __init__(self, parent : QWidget, series : Series):
        """Create a zarr dialog.
        
            Params:
                parent (QWidget): the parent widget
                series (Series): the series
        """
        self.series = series

        super().__init__(parent)

        self.setWindowTitle("Create Zarr")

        vlayout = QVBoxLayout()
        vlayout.setSpacing(10)

        # get the border object
        bobj_row = QHBoxLayout()
        bobj_text = QLabel(self, text="Border object:")
        self.bobj_input = QLineEdit(self)
        resizeLineEdit(self.bobj_input, "X"*15)
        bobj_row.addWidget(bobj_text)
        bobj_row.addWidget(self.bobj_input)
        vlayout.addLayout(bobj_row)

        # get the section range
        sections = sorted(list(series.sections.keys()))
        srange_row = QHBoxLayout()
        srnage_text1 = QLabel(self, text="From section")
        self.srange_input1 = QLineEdit(self)
        self.srange_input1.setText(str(sections[0]))
        resizeLineEdit(self.srange_input1, "0000")
        srange_text2 = QLabel(self, text="to")
        self.srange_input2 = QLineEdit(self)
        self.srange_input2.setText(str(sections[-1]))
        resizeLineEdit(self.srange_input2, "0000")
        srange_row.addWidget(srnage_text1)
        srange_row.addWidget(self.srange_input1)
        srange_row.addWidget(srange_text2)
        srange_row.addWidget(self.srange_input2)
        vlayout.addLayout(srange_row)

        # get the mangification
        mag_row = QHBoxLayout()
        mag_text = QLabel(self, text="Magnification (µm/pix):")
        self.mag_input = QLineEdit(self)
        resizeLineEdit(self.mag_input, "0"*10)
        self.mag_input.setText(
            str(self.series.data["sections"][self.series.current_section]["mag"])
        )
        mag_row.addWidget(mag_text)
        mag_row.addWidget(self.mag_input)
        vlayout.addLayout(mag_row)

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        buttonbox = QDialogButtonBox(QBtn)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        vlayout.addSpacing(10)
        vlayout.addWidget(buttonbox)

        self.setLayout(vlayout)
    
    def accept(self):
        """Overwritten from QDialog."""        
        # check that border object is valid
        bobj = self.bobj_input.text()
        if bobj not in self.series.data["objects"]:
            notify("Border object not in series.")
            return
        
        # check for valid section numbers
        srange = (
            self.srange_input1.text(),
            self.srange_input2.text()
        )
        for s in srange:
            if not s.isnumeric() or int(s) not in self.series.sections:
                notify("Please enter a valid section number.")
                return
        if int(srange[0]) >= int(srange[1]):
            notify("Please enter a valid section range.")
            return
        
        # check for valid mag
        mag = self.mag_input.text()
        if not mag.replace(".", "", 1).isnumeric():
            notify("Please enter a valid magnification.")
            return
        
        super().accept()          

    def exec(self):
        """Run the dialog."""
        confirmed = super().exec()
        if confirmed:

            border_obj = self.bobj_input.text()

            srange = (
                int(self.srange_input1.text()),
                int(self.srange_input2.text()) + 1
            )

            mag = float(self.mag_input.text())

            return (border_obj, srange, mag), True
        
        else:
            return None, False
