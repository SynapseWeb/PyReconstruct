from PySide6.QtWidgets import (
    QWidget, 
    QDialog, 
    QDialogButtonBox, 
    QHBoxLayout, 
    QLabel, 
    QLineEdit, 
    QVBoxLayout, 
    QCheckBox,
    QRadioButton
)

from .color_button import ColorButton

from modules.datatypes import Trace
from modules.gui.utils import notify

class TraceDialog(QDialog):

    def __init__(self, parent : QWidget, traces : list[Trace]=[], name=None, color=None, tags=None, include_radius=False, pos=None):
        """Create an attribute dialog.
        
            Params:
                parent (QWidget): the parent widget
                traces (list): a list of traces
                pos (tuple): the point to create the dialog
        """
        super().__init__(parent)

        # move to desired position
        if pos:
            self.move(*pos)

        self.include_radius = include_radius

        # get the display values if traces have been provided
        if traces:
            trace = traces[0]
            name = trace.name
            color = trace.color
            tags = trace.tags
            fill_style, fill_condition = trace.fill_mode

            # keep track of the traces passed
            self.traces = traces

            # only include radius for editing single palette traces
            if self.include_radius:
                assert(len(traces) == 1)
            
            for trace in traces[1:]:
                if trace.name != name:
                    name = "*"
                if trace.color != color:
                    color = None
                if trace.tags != tags:
                    tags = set()
                if trace.fill_mode[0] != fill_style:
                    fill_style = None
                if trace.fill_mode[1] != fill_condition:
                    fill_condition = None
        else:
            if not name:
                name = "*"
            if not tags:
                tags = set()
            fill_style = None
            fill_condition = None

        self.setWindowTitle("Set Attributes")

        name_row = QHBoxLayout()
        name_text = QLabel(self, text="Name:")
        self.name_input = QLineEdit(self)
        self.name_input.setText(name)
        name_row.addWidget(name_text)
        name_row.addWidget(self.name_input)

        color_row = QHBoxLayout()
        color_text = QLabel(self, text="Color:")
        self.color_input = ColorButton(color, parent)
        color_row.addWidget(color_text)
        color_row.addWidget(self.color_input)
        color_row.addStretch()

        tags_row = QHBoxLayout()
        tags_text = QLabel(self, text="Tags:")
        self.tags_input = QLineEdit(self)
        self.tags_input.setText(", ".join(tags))
        tags_row.addWidget(tags_text)
        tags_row.addWidget(self.tags_input)

        condition_row = QHBoxLayout()
        self.condition_input = QCheckBox("Fill when selected")
        if fill_condition == "selected":
            self.condition_input.setChecked(True)
        else:
            self.condition_input.setChecked(False)
        condition_row.addWidget(self.condition_input)

        style_row = QHBoxLayout()
        style_text = QLabel(self, text="Fill:")
        self.style_none = QRadioButton("None")
        self.style_none.toggled.connect(self.checkDisplayCondition)
        self.style_transparent = QRadioButton("Transparent")
        self.style_transparent.toggled.connect(self.checkDisplayCondition)
        self.style_solid = QRadioButton("Solid")
        self.style_solid.toggled.connect(self.checkDisplayCondition)
        if fill_style == "none":
            self.style_none.setChecked(True)
        elif fill_style == "transparent":
            self.style_transparent.setChecked(True)
        elif fill_style == "solid":
            self.style_solid.setChecked(True)
        else:
            self.checkDisplayCondition()
        style_row.addWidget(style_text)
        style_row.addWidget(self.style_none)
        style_row.addWidget(self.style_transparent)
        style_row.addWidget(self.style_solid)

        if self.include_radius:
            stamp_size_row = QHBoxLayout()
            stamp_size_text = QLabel(self, text="Stamp radius (microns):")
            self.stamp_size_input = QLineEdit(self)
            self.stamp_size_input.setText(str(round(trace.getRadius(), 6)))
            stamp_size_row.addWidget(stamp_size_text)
            stamp_size_row.addWidget(self.stamp_size_input)

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        buttonbox = QDialogButtonBox(QBtn)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        vlayout = QVBoxLayout()
        vlayout.setSpacing(10)
        vlayout.addLayout(name_row)
        vlayout.addLayout(color_row)
        vlayout.addLayout(tags_row)
        vlayout.addLayout(style_row)
        vlayout.addLayout(condition_row)
        if self.include_radius:
            vlayout.addLayout(stamp_size_row)
        vlayout.addWidget(buttonbox)

        self.setLayout(vlayout)
    
    def checkDisplayCondition(self):
        """Determine whether the "fill when selected" checkbox should be displayed."""
        if self.style_transparent.isChecked() or self.style_solid.isChecked():
            self.condition_input.show()
        else:
            self.condition_input.hide()
    
    def accept(self):
        """Overwritten from parent class."""
        if self.include_radius:
            try:
                r = float(self.stamp_size_input.text())
            except ValueError:
                notify("Please enter a valid number.")
                return
            if r < 0:
                notify("Please enter a positive number.")
                return
        
        super().accept()
    
    def exec(self):
        """Run the dialog."""
        confirmed = super().exec()
        if confirmed:
            retlist = []

            # name
            name = self.name_input.text()
            if name == "*" or name == "":
                name = None
            retlist.append(name)

            color = self.color_input.getColor()
            retlist.append(color)

            # color
            tags = self.tags_input.text().split(", ")
            if tags == [""]:
                tags = None
            else:
                tags = set(tags)
            retlist.append(tags)
            
            # fill mode
            if self.style_none.isChecked():
                style = "none"
                condition = "none"
            else:
                if self.style_transparent.isChecked():
                    style = "transparent"
                elif self.style_solid.isChecked():
                    style = "solid"
                else:
                    style = None
                    condition = None
                if self.condition_input.isChecked():
                    condition = "selected"
                else:
                    condition = "unselected"
            retlist.append((style, condition))

            # radius
            if self.include_radius:
                stamp_size = float(self.stamp_size_input.text())
                retlist.append(stamp_size)
            
            return tuple(retlist), True
        
        # user pressed cancel
        else:
            return None, False
