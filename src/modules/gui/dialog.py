from PySide6.QtWidgets import QWidget, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QComboBox, QPushButton, QInputDialog, QCheckBox

from modules.gui.colorbutton import ColorButton

from modules.pyrecon.obj_group_dict import ObjGroupDict
from modules.pyrecon.trace import Trace

class FieldTraceDialog(QDialog):

    def __init__(self, parent : QWidget, traces : list[Trace], pos=None):
        """Create an attribute dialog.
        
            Params:
                parent (QWidget): the parent widget
                traces (list): a list of traces
        """
        super().__init__(parent)

        # move to desired position
        if pos:
            self.move(*pos)

        # get the display values
        trace = traces[0]
        name = trace.name
        color = trace.color
        tags = trace.tags
        for trace in traces[1:]:
            if trace.name != name:
                name = None
            if trace.color != color:
                color = None
            if trace.tags != tags:
                tags = None

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

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonbox = QDialogButtonBox(QBtn)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

        self.vlayout = QVBoxLayout()
        self.vlayout.setSpacing(10)
        self.vlayout.addLayout(self.name_row)
        self.vlayout.addLayout(self.color_row)
        self.vlayout.addLayout(self.tags_row)
        self.vlayout.addWidget(self.buttonbox)

        self.setLayout(self.vlayout)
    
    def exec(self):
        confirmed = super().exec()
        if confirmed:
            name = self.name_input.text()
            color = self.color_input.getColor()
            tags = self.tags_input.text().split(", ")
            if tags == [""]:
                tags = set()
            else:
                tags = set(tags)
            return (
                (
                    name,
                    color,
                    tags,
                ),
                True
            )
        else:
            return None, False

class PaletteTraceDialog(QDialog):

    def __init__(self, parent : QWidget, trace : Trace, stamp_size : float):
        """Create an attribute dialog.
        
            Params:
                parent (QWidget): the parent widget
                trace (Trace): the trace to modify
                stamp_size (float): the existing stamp size
        """
        super().__init__(parent)

        self.setWindowTitle("Set Attributes")

        self.name_row = QHBoxLayout()
        self.name_text = QLabel(self)
        self.name_text.setText("Name:")
        self.name_input = QLineEdit(self)
        self.name_input.setText(trace.name)
        self.name_row.addWidget(self.name_text)
        self.name_row.addWidget(self.name_input)

        self.color_row = QHBoxLayout()
        self.color_text = QLabel(self)
        self.color_text.setText("Color:")
        self.color_input = ColorButton(trace.color, parent)
        self.color_row.addWidget(self.color_text)
        self.color_row.addWidget(self.color_input)
        self.color_row.addStretch()

        self.tags_row = QHBoxLayout()
        self.tags_text = QLabel(self)
        self.tags_text.setText("Tags:")
        self.tags_input = QLineEdit(self)
        self.tags_input.setText(", ".join(trace.tags))
        self.tags_row.addWidget(self.tags_text)
        self.tags_row.addWidget(self.tags_input)

        self.stamp_size_row = QHBoxLayout()
        self.stamp_size_text = QLabel(self)
        self.stamp_size_text.setText("Stamp radius (microns):")
        self.stamp_size_input = QLineEdit(self)
        self.stamp_size_input.setText(str(stamp_size))
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
        self.vlayout.addLayout(self.stamp_size_row)
        self.vlayout.addWidget(self.buttonbox)

        self.setLayout(self.vlayout)
    
    def exec(self):
        confirmed = super().exec()
        if confirmed:
            name = self.name_input.text()
            color = self.color_input.getColor()
            tags = self.tags_input.text().split(", ")
            if tags == [""]:
                tags = set()
            else:
                tags = set(tags)
            stamp_size = self.stamp_size_input.text()
            try:
                stamp_size = float(stamp_size)
            except ValueError:
                stamp_size = None
            return (
                (
                    name,
                    color,
                    tags,
                    stamp_size
                ),
                True
            )
        else:
            return None, False


class ObjectGroupDialog(QDialog):

    def __init__(self, parent : QWidget, objgroupdict : ObjGroupDict, new_group=True):
        """Create an object group dialog.
        
            Params:
                parent (QWidget): the parent widget
                objgroupdict (ObjGroupDict): object containing information on object groups
                new_group (bool): whether or not to include new group button
        """
        super().__init__(parent)

        self.setWindowTitle("Object Group")

        self.group_row = QHBoxLayout()
        self.group_text = QLabel(self)
        self.group_text.setText("Group:")
        self.group_input = QComboBox(self)
        self.group_input.addItem("")
        self.group_input.addItems(sorted(objgroupdict.getGroupList()))
        self.group_input.resize(self.group_input.sizeHint())
        self.group_row.addWidget(self.group_text)
        self.group_row.addWidget(self.group_input)
        if new_group:
            self.newgroup_bttn = QPushButton(self, "new_group", text="New Group...")
            self.newgroup_bttn.clicked.connect(self.newGroup)
            self.group_row.addWidget(self.newgroup_bttn)

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonbox = QDialogButtonBox(QBtn)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

        self.vlayout = QVBoxLayout()
        self.vlayout.setSpacing(10)
        self.vlayout.addLayout(self.group_row)
        self.vlayout.addWidget(self.buttonbox)

        self.setLayout(self.vlayout)
    
    def newGroup(self):
        """Add a new group to the list."""
        new_group_name, confirmed = QInputDialog.getText(self, "New Object Group", "New group name:")
        if not confirmed:
            return
        self.group_input.addItem(new_group_name)
        self.group_input.setCurrentText(new_group_name)
        self.group_input.resize(self.group_input.sizeHint())
        
    def exec(self):
        confirmed = super().exec()
        text = self.group_input.currentText()
        if confirmed and text:
            return self.group_input.currentText(), True
        else:
            return "", False


class ObjectTableColumnsDialog(QDialog):

    def __init__(self, parent, columns):
        """Create an object table column dialog.
        
            Params:
                columns (dict): the existing columns and their status
        """
        super().__init__(parent)

        self.setWindowTitle("Object Table Columns")

        self.title_text = QLabel(self)
        self.title_text.setText("Object table columns:")

        self.cbs = []
        for c in columns:
            c_cb = QCheckBox(self)
            c_cb.setText(c)
            c_cb.setChecked(columns[c])
            self.cbs.append(c_cb)

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonbox = QDialogButtonBox(QBtn)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

        self.vlayout = QVBoxLayout(self)
        self.vlayout.setSpacing(10)
        self.vlayout.addWidget(self.title_text)
        for c_row in self.cbs:
            self.vlayout.addWidget(c_row)
        self.vlayout.addWidget(self.buttonbox)

        self.setLayout(self.vlayout)
    
    def exec(self):
        confirmed = super().exec()
        if confirmed:
            columns = {}
            for cb in self.cbs:
                columns[cb.text()] = cb.isChecked()
            return columns, True
        else:
            return {}, False
        