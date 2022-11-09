from PySide6.QtWidgets import QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout, QComboBox, QPushButton, QInputDialog, QSizePolicy

from modules.gui.colorbutton import ColorButton

from modules.pyrecon.obj_group_dict import ObjGroupDict

class AttributeDialog(QDialog):

    def __init__(self, parent, name="", color=None):
        super().__init__(parent)

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

        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.buttonbox = QDialogButtonBox(QBtn)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

        self.vlayout = QVBoxLayout()
        self.vlayout.setSpacing(10)
        self.vlayout.addLayout(self.name_row)
        self.vlayout.addLayout(self.color_row)
        self.vlayout.addWidget(self.buttonbox)

        self.setLayout(self.vlayout)
    
    def exec(self):
        confirmed = super().exec()
        if confirmed:
            return self.name_input.text(), self.color_input.getColor(), True
        else:
            return "", (), False

class ObjectGroupDialog(QDialog):

    def __init__(self, parent, objgroupdict : ObjGroupDict):
        super().__init__(parent)

        self.setWindowTitle("Object Group")

        self.group_row = QHBoxLayout()
        self.group_text = QLabel(self)
        self.group_text.setText("Group:")
        self.group_input = QComboBox(self)
        self.group_input.addItems(objgroupdict.getGroupList())
        self.group_input.resize(self.group_input.sizeHint())
        self.newgroup_bttn = QPushButton(self, "new_group", text="New Group...")
        self.newgroup_bttn.clicked.connect(self.newGroup)
        self.group_row.addWidget(self.group_text)
        self.group_row.addWidget(self.group_input)
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
        new_group_name, confirmed = QInputDialog.getText(self, "New Object Group", "New group name:")
        if not confirmed:
            return
        self.group_input.addItem(new_group_name)
        self.group_input.setCurrentText(new_group_name)
        
    def exec(self):
        confirmed = super().exec()
        text = self.group_input.currentText()
        if confirmed and text:
            return self.group_input.currentText(), True
        else:
            return "", False





            