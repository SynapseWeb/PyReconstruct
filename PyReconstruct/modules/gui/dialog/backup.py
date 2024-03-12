import os
from datetime import datetime

from PySide6.QtWidgets import (
    QDialog, 
    QDialogButtonBox, 
    QLabel, 
    QLineEdit, 
    QVBoxLayout,
    QHBoxLayout,
    QCheckBox
)

from .helper import BrowseWidget

from PyReconstruct.modules.datatypes import Series
from PyReconstruct.modules.gui.utils import notify

def getDateTime():
    dt = datetime.now()
    d = f"{dt.year % 1000}-{dt.month:02d}-{dt.day:02d}"
    t = f"{dt.hour:02d}-{dt.minute:02d}"
    return d, t

class BackupDialog(QDialog):

    def __init__(self, parent, series : Series):
        """Create a dialog for brightness/contrast."""
        super().__init__(parent)
        self.setWindowTitle("Backup Series")
        self.series = series

        name = series.name
        date, time = getDateTime()
        user = series.user
        self.fp = ""

        vlayout = QVBoxLayout()

        # create the directory widget first
        hbl = QHBoxLayout()
        bdir = series.getOption("manual_backup_dir")
        if not os.path.isdir(bdir):
            bdir = ""
        self.dir_widget = BrowseWidget(self, "dir", bdir)
        hbl.addWidget(QLabel(self, text="Save Folder:"))
        hbl.addWidget(self.dir_widget)
        vlayout.addLayout(hbl)

        # create the delimiter widget
        r = QHBoxLayout()
        lbl = QLabel(self, text="Delimiter:")
        self.delimiter_le = QLineEdit(self, text="-")
        self.delimiter_le.textChanged.connect(self.updateWidgets)
        r.addWidget(lbl)
        r.addWidget(self.delimiter_le)
        vlayout.addLayout(r)

        self.widgets = {}

        widget_info = [
            ("name", name),
            ("date", date),
            ("time", time),
            ("user", user),
            ("comment", "")
        ]

        self.save_name_lbl = QLabel(self)

        # create the widgets for each field
        for k, v in widget_info:
            r = QHBoxLayout()
            cb = QCheckBox(self)
            cb.setText(f"{k.title()}:")
            cb.setChecked(series.getOption(f"manual_backup_{k}"))
            cb.stateChanged.connect(self.updateWidgets)
            le = QLineEdit(self, text=v)
            le.textChanged.connect(self.updateWidgets)
            r.addWidget(cb)
            r.addWidget(le)
            vlayout.addLayout(r)
            self.widgets[k] = (cb, le)

        # display name
        vlayout.addSpacing(10)
        vlayout.addWidget(QLabel(self, text="Save File Name:"))
        vlayout.addWidget(self.save_name_lbl)
        
        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        buttonbox = QDialogButtonBox(QBtn)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        vlayout.addWidget(buttonbox)

        self.setLayout(vlayout)
        self.updateWidgets()
    
    def updateWidgets(self):
        """Update the display widgets."""
        l = []
        dl = self.delimiter_le.text()
        for cb, le in self.widgets.values():
            if cb.isChecked():
                le.setEnabled(True)
                l.append(le.text().replace(" ", dl))
            else:
                le.setEnabled(False)
        self.save_name_lbl.setText(dl.join(l))
    
    def accept(self):
        """Overwritten from parent class."""
        bdir = self.dir_widget.text()
        if not os.path.isdir(bdir):
            notify("Please enter a valid directory.")
            return
        fname = f"{self.save_name_lbl.text()}.jser"
        self.fp = os.path.join(bdir, fname)

        # set the series options
        self.series.setOption("manual_backup_dir", bdir)
        for name, (cb, le) in self.widgets.items():
            self.series.setOption(
                f"manual_backup_{name}",
                cb.isChecked()
            )

        super().accept()
    
    def exec(self):
        "Run the dialog."
        confirmed = super().exec()
        if confirmed:
            return self.fp, True
        else:
            return None, False