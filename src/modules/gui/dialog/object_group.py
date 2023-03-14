from PySide6.QtWidgets import (
    QWidget, 
    QDialog, 
    QDialogButtonBox, 
    QHBoxLayout, 
    QLabel, 
    QVBoxLayout, 
    QComboBox, 
    QPushButton, 
    QInputDialog
)

from modules.pyrecon import ObjGroupDict


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
        self.vlayout.addSpacing(10)
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
        """Run the dialog."""
        confirmed = super().exec()
        text = self.group_input.currentText()
        if confirmed and text:
            return self.group_input.currentText(), True
        else:
            return "", False