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
from .shape_button import ShapeButton

from modules.datatypes import Trace
from modules.gui.utils import notify

class TraceDialog(QDialog):

    def __init__(
            self,
            parent : QWidget, 
            traces : list[Trace]=[], 
            name=None,
            color=None,
            tags=None,
            is_palette=False,
            inc_sec_range=False,
            pos=None):
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

        self.is_palette = is_palette

        # get the display values if traces have been provided
        if traces:
            trace = traces[0]
            name = trace.name
            color = trace.color
            ct = trace.copy()
            ct.resize(1)
            points = ct.points
            tags = trace.tags
            fill_style, fill_condition = trace.fill_mode

            # keep track of the traces passed
            self.traces = traces

            # only include radius for editing single palette traces
            if self.is_palette:
                assert(len(traces) == 1)
            
            for trace in traces[1:]:
                if trace.name != name:
                    name = "*"
                if trace.color != color:
                    color = None
                if trace.points != points:
                    points = None
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
        self.color_input = ColorButton(color, self)
        color_row.addWidget(color_text)
        color_row.addWidget(self.color_input)
        color_row.addStretch()

        if self.is_palette:
            shape_row = QHBoxLayout()
            shape_text = QLabel(self, text="Shape:")
            self.shape_input = ShapeButton(points, self)
            shape_row.addWidget(shape_text)
            shape_row.addWidget(self.shape_input)
            shape_row.addStretch()

        tags_row = QHBoxLayout()
        tags_text = QLabel(self, text="Tags:")
        self.tags_input = QLineEdit(self)
        self.tags_input.setText(", ".join(tags))
        tags_row.addWidget(tags_text)
        tags_row.addWidget(self.tags_input)

        self.selected_input = QCheckBox("Fill when selected")
        if fill_condition in ("selected", "always"):
            self.selected_input.setChecked(True)
        else:
            self.selected_input.setChecked(False)

        self.unselected_input = QCheckBox("Fill when unselected")
        if fill_condition in ("unselected", "always"):
            self.unselected_input.setChecked(True)
        else:
            self.unselected_input.setChecked(False)

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

        if self.is_palette:
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
        if self.is_palette: vlayout.addLayout(shape_row)
        vlayout.addLayout(tags_row)
        vlayout.addLayout(style_row)
        vlayout.addWidget(self.selected_input)
        vlayout.addWidget(self.unselected_input)
        if self.is_palette: vlayout.addLayout(stamp_size_row)
        vlayout.addWidget(buttonbox)

        self.setLayout(vlayout)
    
    def checkDisplayCondition(self):
        """Determine whether the "fill when selected" checkbox should be displayed."""
        if self.style_transparent.isChecked() or self.style_solid.isChecked():
            self.selected_input.show()
            self.selected_input.setChecked(True)
            self.unselected_input.show()
            self.unselected_input.setChecked(True)
        else:
            self.selected_input.hide()
            self.selected_input.setChecked(False)
            self.unselected_input.hide()
            self.unselected_input.setChecked(True)
    
    def accept(self):
        """Overwritten from parent class."""
        if self.is_palette:
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
            # create a dummy trace to return
            trace = Trace(None, None, None)

            # name
            name = self.name_input.text()
            if name == "*" or name == "":
                name = None
            trace.name = name

            color = self.color_input.getColor()
            trace.color = color

            # color
            tags = self.tags_input.text().split(", ")
            if tags == [""]:
                tags = None
            else:
                tags = set(tags)
            trace.tags = tags

            # shape
            if self.is_palette:
                points = self.shape_input.getShape()
                trace.points = points
            else:
                trace.points = None
            
            # fill mode
            if self.style_none.isChecked():
                style = "none"
                condition = "none"
            elif self.style_transparent.isChecked():
                style = "transparent"
            elif self.style_solid.isChecked():
                style = "solid"
            else:
                style = None
                condition = None
            
            if style in ("transparent", "solid"):
                sel = self.selected_input.isChecked()
                unsel = self.unselected_input.isChecked()
                if sel and unsel:
                    condition = "always"
                elif sel:
                    condition = "selected"
                elif unsel:
                    condition = "unselected"
                else:
                    style = "none"
                    condition = "none"
            
            trace.fill_mode = (style, condition)

            # radius
            if self.is_palette:
                stamp_size = float(self.stamp_size_input.text())
                trace.resize(stamp_size)

            return trace, True
        
        # user pressed cancel
        else:
            return None, False
