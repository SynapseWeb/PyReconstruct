import os
import webbrowser
from datetime import datetime

from PySide6.QtWidgets import (
    QDialog, 
    QDialogButtonBox, 
    QLabel, 
    QLineEdit, 
    QVBoxLayout,
    QHBoxLayout,
    QCheckBox,
    QPushButton
)

from .helper import BrowseWidget, BorderedWidget

from PyReconstruct.modules.datatypes import Series
from PyReconstruct.modules.gui.utils import notify

class BackupCommentDialog(QDialog):

    def __init__(self, parent, series : Series):
        """Create a dialog for backing up."""
        super().__init__(parent)
        self.setWindowTitle("Backup With Comment")
        self.mainwindow = parent
        self.series = series

        vlayout = QVBoxLayout()

        vlayout.addWidget(QLabel(self, text="Enter comment:\n(Press enter to leave blank)"))
        self.comment_le = QLineEdit(self)
        self.comment_le.textChanged.connect(self.updateWidgets)
        vlayout.addWidget(self.comment_le)

        vlayout.addSpacing(10)
        vlayout.addWidget(QLabel(self, text="Backup file:"))
        self.fname_le = QLabel(self)
        vlayout.addWidget(self.fname_le)
        
        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        buttonbox = QDialogButtonBox(QBtn)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        self.open_settings_bttn = QPushButton(self, text="Modify name structure")
        self.open_settings = False
        self.open_settings_bttn.clicked.connect(self.openSettings)
        buttonbox.addButton(self.open_settings_bttn, QDialogButtonBox.ResetRole)

        vlayout.addWidget(buttonbox)

        self.setLayout(vlayout)
        self.updateWidgets()
    
    def updateWidgets(self):
        """Update the display widgets."""
        comment = self.comment_le.text()
        fp = self.series.getBackupPath(comment)
        fname = os.path.basename(fp)
        self.fname_le.setText(fname)

    
    def openSettings(self):
        """Open the backup settings."""
        self.open_settings = True
        self.accept()
    
    def exec(self):
        "Run the dialog."
        confirmed = super().exec()
        return (self.comment_le.text(), self.open_settings), confirmed