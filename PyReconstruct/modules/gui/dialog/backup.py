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

from .helper import BrowseWidget, resizeLineEdit

from PyReconstruct.modules.datatypes import Series
from PyReconstruct.modules.gui.utils import notify

def getDateTime():
    dt = datetime.now()
    d = f"{dt.year % 1000}",f"{dt.month:02d}",f"{dt.day:02d}"
    t = f"{dt.hour:02d}",f"{dt.minute:02d}"
    return d, t

class BackupDialog(QDialog):

    def __init__(self, parent, series : Series):
        """Create a dialog for brightness/contrast."""
        super().__init__(parent)
        self.setWindowTitle("Backup Series")
        self.series = series

        name = series.name
        self.date, self.time = getDateTime()

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
        lbl = QLabel(self, text="Overall Delimiter:")
        self.delimiter_le = QLineEdit(
            self, 
            text=self.series.getOption("manual_backup_delimiter")
        )
        self.delimiter_le.textChanged.connect(self.updateWidgets)
        r.addWidget(lbl)
        r.addWidget(self.delimiter_le)
        vlayout.addLayout(r)

        self.widgets = {}

        widget_info = [
            ("name", name),
            ("date", ""),  # updated later
            ("time", ""),  # updated later
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

            # manually add widgets for date and time delimiters
            if k in ("date", "time"):
                le.setEnabled(False)
                r.addWidget(QLabel(self, text="Delimiter:"))
                dle = QLineEdit(
                    self,
                    text=self.series.getOption(f"manual_backup_{k}_delimiter")
                )
                resizeLineEdit(dle, "000")
                dle.textChanged.connect(self.updateWidgets)
                setattr(self, f"{k}_delimiter_le", dle)
                r.addWidget(dle)

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
        for name, (cb, le) in self.widgets.items():
            if name in ("date", "time"):
                dle = getattr(self, f"{name}_delimiter_le")
                d = dle.text()
                le.setText(d.join(getattr(self, name)))
            if cb.isChecked():
                l.append(le.text().replace(" ", dl))
                    
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
        self.series.setOption(
            "manual_backup_delimiter",
            self.delimiter_le.text()
        )
        for s in ("date", "time"):
            self.series.setOption(
                f"manual_backup_{s}_delimiter",
                getattr(self, f"{s}_delimiter_le").text()
            )

        super().accept()
    
    def exec(self):
        "Run the dialog."
        confirmed = super().exec()
        if confirmed:
            return self.fp, True
        else:
            return None, False