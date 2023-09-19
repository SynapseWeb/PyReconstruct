import os

from PySide6.QtWidgets import (
    QWidget,
    QDialog, 
    QDialogButtonBox, 
    QLabel, 
    QLineEdit,
    QComboBox,
    QVBoxLayout,
    QHBoxLayout,
    QCheckBox,
    QRadioButton
)

from .helper import resizeLineEdit, BrowseWidget
from .color_button import ColorButton

from modules.gui.utils import notify

class InputField():

    def __init__(self, type, widget, check_params=None, required=False):
        self.type = type
        self.widget = widget
        self.check_params = check_params
        self.required = required
    
    def getResponse(self):
        if self.type == "text":
            t = self.widget.text()
            if not t and self.required:
                notify("Please enter a response.")
                return None, False
            else:
                return t, True
        elif self.type == "int":
            if not self.widget.text():
                if self.required:
                    notify("Please enter an integer.")
                    return None, False
                else:
                    return None, True
            try:
                n = int(self.widget.text())
                if self.check_params:
                    if n in self.check_params:
                        return n, True
                    else:
                        notify("Please enter a valid integer.")
                        return None, False
                else:
                    return n, True
            except ValueError:
                notify("Please enter a valid integer.")
                return None, False
        elif self.type == "float":
            if not self.widget.text():
                if self.required:
                    notify("Please enter a number.")
                    return None, False
                else:
                    return None, True
            try:
                n = float(self.widget.text())
                if self.check_params:
                    lower, upper = tuple(self.check_params)
                    if lower <= n <= upper:
                        return n, True
                    else:
                        notify("Please enter a valid number.")
                        return None, False
                else:
                    return n, True
            except ValueError:
                notify("Please enter a valid number.")
                return None, False
        elif self.type == "combo":
            t = self.widget.currentText()
            if t == "" and self.required:
                notify("Please select a field from the dropdown menu.")
                return None, False
            else:
                return t, True
        elif self.type == "check" or self.type == "radio":
            response = []
            layout = self.widget.layout()
            for i in range(layout.count()):
                bttn = layout.itemAt(i).widget()
                response.append((bttn.text(), bttn.isChecked()))
            return response, True
        elif self.type == "file" or self.type == "dir":
            r = self.widget.text()
            if r:
                if os.path.isdir(r) or os.path.isfile(r):
                    return r, True
                else:
                    notify("Please select a valid path.")
                    return None, False
            else:
                if self.required:
                    notify("Please enter a path.")
                    return None, False
                else:
                    return None, True
        elif self.type == "color":
            c = self.widget.getColor()
            if c is None:
                if self.required:
                    notify("Please select a color.")
                    return None, False
                else:
                    return None, True
            else:
                return c, True


class QuickDialog(QDialog):

    def __init__(self, parent, structure : list, title : str):
        """Create a quick dialog from a given structure.
        
            Params:
                parent (QWidget): the widget containing the dialog
                structure (list): the structure of the dialog
                title (str): the title of the dialog
        """
        super().__init__(parent)

        self.setWindowTitle(title)
        vlayout = QVBoxLayout()
        self.inputs = []

        for row_structure in structure:
            row_layout = QHBoxLayout()
            for item in row_structure:
                if type(item) is str:  # Label
                    row_layout.addWidget(QLabel(self, text=item))
                else:
                    # checking for leading bool to mark required status
                    if type(item[0]) is bool:
                        required = item[0]
                        item = item[1:]
                    else:
                        required = False
                    widget_type = item[0]
                    params = item[1:]
                    if widget_type == "text":  # Text input
                        # Params structure: str
                        text = params[0]
                        le = QLineEdit(text, self)
                        row_layout.addWidget(le)
                        self.inputs.append(InputField(widget_type, le, required=required))
                    elif widget_type == "int" or widget_type == "float": 
                        # Params structure: int, optional: list[int]
                        n = params[0]
                        if len(params) > 1:
                            options = params[1]
                        else:
                            options = None
                        if n is None:
                            le = QLineEdit("", self)
                        else:
                            le = QLineEdit(str(n), self)
                        resizeLineEdit(le, "000000")
                        row_layout.addWidget(le)
                        self.inputs.append(InputField(widget_type, le, options, required=required))
                    elif widget_type == "combo":
                        # Params structure: list[str], optional: str
                        options = params[0]
                        combo = QComboBox(self)
                        combo.addItems([""] + list(options))
                        if len(params) > 1:
                            selected = params[1]
                            if selected:
                                combo.setCurrentText(selected)
                        row_layout.addWidget(combo)
                        self.inputs.append(InputField(widget_type, combo, required=required))
                    elif widget_type == "check" or widget_type == "radio":
                        # Params structure list[(str, bool)]
                        container = QWidget(self)
                        vl = QVBoxLayout()
                        for text, checked in params:
                            if widget_type == "check":
                                bttn = QCheckBox(text, container)
                            else:
                                bttn = QRadioButton(text, container)
                            bttn.setChecked(checked)
                            vl.addWidget(bttn)
                        container.setLayout(vl)
                        row_layout.addWidget(container)
                        self.inputs.append(InputField(widget_type, container, required=required))
                    elif widget_type == "file" or widget_type == "dir":
                        # Params structure: str (default filepath), str (filter; only for file)
                        fp = params[0]
                        if widget_type == "file":
                            filter = params[1]
                        else:
                            filter = None
                        bw = BrowseWidget(self, type=widget_type, default_fp=fp, filter=filter)
                        row_layout.addWidget(bw)
                        self.inputs.append(InputField(widget_type, bw, required=required))
                    elif widget_type == "color":
                        # Params structure: tuple (optional)
                        color = params[0]
                        cb = ColorButton(color, self)
                        row_layout.addWidget(cb)
                        self.inputs.append(InputField(widget_type, cb, required=required))

            vlayout.addLayout(row_layout)

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        buttonbox = QDialogButtonBox(QBtn)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        vlayout.addWidget(buttonbox)

        self.setLayout(vlayout)
    
    def accept(self):
        """Overwritten from parent class."""
        self.responses = []
        for input in self.inputs:
            r, is_valid = input.getResponse()
            if not is_valid:
                return
            else:
                self.responses.append(r)
        
        super().accept()
    
    def exec(self):
        "Run the dialog."
        confirmed = super().exec()
        if confirmed:
            return tuple(self.responses), True
        else:
            return None, False
    
    def get(parent : QWidget, structure : list, title="Dialog"):
        """Create a quick dialog and return the inputs.
        
            Params:
                parent (QWidget): the parent of the input dialog
                structure (list): the structure of the input dialog
                title (str): the title of the dialog
        """
        return QuickDialog(parent, structure, title).exec()