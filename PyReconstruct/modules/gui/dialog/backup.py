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

from .helper import BrowseWidget, resizeLineEdit

from PyReconstruct.modules.datatypes import Series
from PyReconstruct.modules.gui.utils import notify

class BackupDialog(QDialog):

    def __init__(self, parent, series : Series):
        """Create a dialog for brightness/contrast."""
        super().__init__(parent)
        self.setWindowTitle("Backup Series")
        self.series = series

        name = series.code
        self.now = datetime.now()

        user = series.user
        self.fp = ""

        vlayout = QVBoxLayout()

        # create the directory widget first
        hbl = QHBoxLayout()
        bdir = series.getOption("manual_backup_dir")
        if not os.path.isdir(bdir):
            bdir = ""
        self.dir_widget = BrowseWidget(self, "dir", bdir)
        hbl.addWidget(QLabel(self, text="Backup Folder:"))
        hbl.addWidget(self.dir_widget)
        vlayout.addLayout(hbl)

        # create the delimiter + utc widget
        r = QHBoxLayout()
        lbl = QLabel(self, text="Delimiter:")
        self.delimiter_le = QLineEdit(
            self, 
            text=self.series.getOption("manual_backup_delimiter")
        )
        # resizeLineEdit(self.delimiter_le, "000")
        self.delimiter_le.textChanged.connect(self.updateWidgets)
        r.addWidget(lbl)
        r.addWidget(self.delimiter_le)

        self.utc_cb = QCheckBox(self, text="Use UTC for date and time")
        self.utc_cb.setToolTip(utc_tip)
        self.utc_cb.setChecked(self.series.getOption("manual_backup_utc"))
        self.utc_cb.stateChanged.connect(self.updateNow)
        r.addWidget(self.utc_cb)

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

            if k in ("date", "time"):
                le.setText(self.series.getOption(f"manual_backup_{k}_str"))
                bttn = QPushButton(self, text="?")
                bttn.clicked.connect(openCodesLink)
                tip = date_tip if k == "date" else time_tip
                bttn.setToolTip(tip)
                r.addWidget(bttn)

            vlayout.addLayout(r)
            self.widgets[k] = (cb, le)

        # display name
        vlayout.addSpacing(10)
        vlayout.addWidget(QLabel(self, text="Backup File Name:"))
        vlayout.addWidget(self.save_name_lbl)
        
        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        buttonbox = QDialogButtonBox(QBtn)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        vlayout.addWidget(buttonbox)

        self.setLayout(vlayout)
        self.updateWidgets()
    
    def updateNow(self, utc : bool):
        """Toggle the time between local and UTC time."""
        if utc:
            self.now = datetime.utcnow()
        else:
            self.now = datetime.now()
        self.updateWidgets()
    
    def updateWidgets(self):
        """Update the display widgets."""
        l = []
        dl = self.delimiter_le.text()
        for name, (cb, le) in self.widgets.items():
            if cb.isChecked() and le.text():
                if name in ("date", "time"):
                    text = self.now.strftime(le.text())
                else:
                    text = le.text()
                l.append(text.replace(" ", dl))
        self.save_name_lbl.setText(dl.join(l))
    
    def accept(self):
        """Overwritten from parent class."""
        bdir = self.dir_widget.text()
        if not os.path.isdir(bdir):
            notify("Please enter a valid directory.")
            return
        
        fname = self.save_name_lbl.text() + ".jser"
        self.fp = os.path.join(bdir, fname)

        ## do not overwrite existing backups
        if os.path.exists(self.fp):
            time_now = datetime.now().strftime("%H%M%S")
            unique_fname = self.save_name_lbl.text() + "-" + time_now + ".jser"
            self.fp = os.path.join(bdir, unique_fname)

        # set the series options
        self.series.setOption("manual_backup_dir", bdir)
        for name, (cb, le) in self.widgets.items():
            self.series.setOption(
                f"manual_backup_{name}",
                cb.isChecked()
            )
            if name in ("date", "time"):
                self.series.setOption(
                    f"manual_backup_{name}_str", 
                    le.text()
                )
        self.series.setOption(
            "manual_backup_delimiter",
            self.delimiter_le.text()
        )
        self.series.setOption(
            "manual_backup_utc",
            self.utc_cb.isChecked()
        )

        super().accept()
    
    def exec(self):
        "Run the dialog."
        confirmed = super().exec()
        if confirmed:
            return self.fp, True
        else:
            return None, False
        
utc_tip = """UTC stands for Coordinated Universal Time
UTC is used as a standard for all time zones. It lines up with
GMT (Greenwich Mean Time)."""

date_tip = """Date codes:
%y = two-digit year (ex. 24)
%Y = four-digit year (ex. 2024)
%m = two-digit month (ex. 04)
%d = two-digit day (ex. 02)

Click for more information."""

time_tip = """Time codes:
%H = two-digit hour (24-hour clock; ex. 14)
%I = two-digit hour (12-hour clock; ex. 02)
%p = AM or PM
%M = two-digit minute (ex. 47)
%S = two-digit second (ex. 13)

Click for more information."""

def openCodesLink():
    dtcodes_link = "https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes"
    webbrowser.open(dtcodes_link)
