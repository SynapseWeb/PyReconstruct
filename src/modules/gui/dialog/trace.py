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

from modules.pyrecon import Trace

class TraceDialog(QDialog):

    def __init__(self, parent : QWidget, traces : list[Trace]=[], name=None, include_radius=False, pos=None):
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
            color = None
            tags = set()
            fill_style = None
            fill_condition = None

        self.setWindowTitle("Set Attributes")

        self.name_row = QHBoxLayout()
        self.name_text = QLabel(self)
        self.name_text.setText("Name:")
        self.name_input = QLineEdit(self)
        self.name_input.setText(name)
        self.name_row.addWidget(self.name_text)
        self.name_row.addWidget(self.name_input)

        self.color_row = QHBoxLayout()
        self.color_text = QLabel(self)
        self.color_text.setText("Color:")
        self.color_input = ColorButton(color, parent)
        self.color_row.addWidget(self.color_text)
        self.color_row.addWidget(self.color_input)
        self.color_row.addStretch()

        self.tags_row = QHBoxLayout()
        self.tags_text = QLabel(self)
        self.tags_text.setText("Tags:")
        self.tags_input = QLineEdit(self)
        self.tags_input.setText(", ".join(tags))
        self.tags_row.addWidget(self.tags_text)
        self.tags_row.addWidget(self.tags_input)

        self.condition_row = QHBoxLayout()
        self.condition_input = QCheckBox("Fill when selected")
        if fill_condition == "selected":
            self.condition_input.setChecked(True)
        else:
            self.condition_input.setChecked(False)
        self.condition_row.addWidget(self.condition_input)

        self.style_row = QHBoxLayout()
        self.style_text = QLabel(self)
        self.style_text.setText("Fill:")
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
        self.style_row.addWidget(self.style_text)
        self.style_row.addWidget(self.style_none)
        self.style_row.addWidget(self.style_transparent)
        self.style_row.addWidget(self.style_solid)

        if self.include_radius:
            self.stamp_size_row = QHBoxLayout()
            self.stamp_size_text = QLabel(self)
            self.stamp_size_text.setText("Stamp radius (microns):")
            self.stamp_size_input = QLineEdit(self)
            self.stamp_size_input.setText(str(round(trace.getRadius(), 6)))
            self.stamp_size_row.addWidget(self.stamp_size_text)
            self.stamp_size_row.addWidget(self.stamp_size_input)

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonbox = QDialogButtonBox(QBtn)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

        self.vlayout = QVBoxLayout()
        self.vlayout.setSpacing(10)
        self.vlayout.addLayout(self.name_row)
        self.vlayout.addLayout(self.color_row)
        self.vlayout.addLayout(self.tags_row)
        self.vlayout.addLayout(self.style_row)
        self.vlayout.addLayout(self.condition_row)
        if self.include_radius:
            self.vlayout.addLayout(self.stamp_size_row)
        self.vlayout.addWidget(self.buttonbox)

        self.setLayout(self.vlayout)
    
    def checkDisplayCondition(self):
        """Determine whether the "fill when selected" checkbox should be displayed."""
        if self.style_transparent.isChecked() or self.style_solid.isChecked():
            self.condition_input.show()
        else:
            self.condition_input.hide()
    
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
                stamp_size = self.stamp_size_input.text()
                try:
                    stamp_size = float(stamp_size)
                except ValueError:
                    stamp_size = None
                retlist.append(stamp_size)
            
            return tuple(retlist), True
        
        # user pressed cancel
        else:
            return None, False