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

from modules.datatypes import Series
from modules.gui.utils import notify

class CreateZarrDialog(QDialog):

    def __init__(self, parent : QWidget, series : Series):
        """Create a zarr dialog.
        
            Params:
                parent (QWidget): the parent widget
                objgroupdict (ObjGroupDict): object containing information on object groups
                new_group (bool): whether or not to include new group button
        """
        self.series = series

        # save the series to jser file
        self.series.saveJser()

        super().__init__(parent)

        self.setWindowTitle("Create Zarr")

        vlayout = QVBoxLayout()
        vlayout.setSpacing(10)

        # create the group combo box inputs
        self.group_widgets = []
        for i in range(5):
            row = QHBoxLayout()
            text = QLabel(self)
            text.setText("Group:")
            input = QComboBox(self)
            input.addItem("")
            input.addItems(sorted(series.object_groups.getGroupList()))
            input.resize(input.sizeHint())
            row.addWidget(text)
            row.addWidget(input)
            if i != 0:
                text.hide()
                input.hide()
            self.group_widgets.append((text, input))
            vlayout.addLayout(row)
        self.inputs = 1

        # create buttons for adding and removing group inputs
        addremove_row = QHBoxLayout()
        addremove_row.addSpacing(10)
        self.add_bttn = QPushButton(text="Add Group", parent=self)
        self.add_bttn.clicked.connect(self.addInput)
        self.remove_bttn = QPushButton(text="Remove Group", parent=self)
        self.remove_bttn.clicked.connect(self.removeInput)
        addremove_row.addWidget(self.remove_bttn)
        addremove_row.addWidget(self.add_bttn)
        self.remove_bttn.hide()
        vlayout.addLayout(addremove_row)

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
            str(self.series.section_mags[self.series.current_section])
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
    
    def addInput(self):
        """Add a group input."""
        if self.inputs >= 5:
            return
        text, input = self.group_widgets[self.inputs]
        text.show()
        input.show()
        self.inputs += 1
        self.updateButtons()
    
    def removeInput(self):
        """Remove a group input."""
        if self.inputs <= 1:
            return
        text, input = self.group_widgets[self.inputs-1]
        text.hide()
        input.hide()
        self.inputs -= 1
        self.updateButtons()
    
    def updateButtons(self):
        """Show/hide buttons according to number of inputs."""
        if self.inputs < 5:
            self.add_bttn.show()
        else:
            self.add_bttn.hide()
        if self.inputs > 1:
            self.remove_bttn.show()
        else:
            self.remove_bttn.hide()
    
    def accept(self):
        """Overwritten from QDialog."""        
        # check that border object is valid
        bobj = self.bobj_input.text()
        if bobj not in self.series.objs:
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
        if srange[0] >= srange[1]:
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
            groups = set()
            for text, input in self.group_widgets:
                group = input.currentText()
                if group:
                    groups.add(group)
            groups = list(groups)

            border_obj = self.bobj_input.text()

            srange = (
                int(self.srange_input1.text()),
                int(self.srange_input2.text()) + 1
            )

            mag = float(self.mag_input.text())

            return (groups, border_obj, srange, mag), True
        
        else:
            return None, False