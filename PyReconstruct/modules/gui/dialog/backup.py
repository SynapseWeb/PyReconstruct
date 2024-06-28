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

class BackupDialog(QDialog):

    def __init__(self, parent, series : Series, include_confirm=True):
        """Create a dialog for backing up.
        
            Params:
                series (Series): the series obj
                include_confirm (bool): True if dialog should include OK and Cancel buttons
        """
        super().__init__(parent)
        self.setWindowTitle("Backup Settings")
        self.series = series

        utc = self.series.getOption("utc")
        self.now = datetime.utcnow() if utc else datetime.now()
        self.fp = ""

        vlayout = QVBoxLayout()
        vlayout1 = QVBoxLayout()
        vlayout2 = QVBoxLayout()

        # create the directory widget first
        hbl = QHBoxLayout()
        bdir = series.getOption("backup_dir")
        if not os.path.isdir(bdir):
            bdir = ""
        self.dir_widget = BrowseWidget(self, "dir", bdir)
        hbl.addWidget(QLabel(self, text="Backup Folder:"))
        hbl.addWidget(self.dir_widget)
        vlayout1.addLayout(hbl)

        # checkbox for autobackup
        self.auto_cb = QCheckBox(self, text="Auto-backup (create backup on every save)")
        self.auto_cb.setChecked(self.series.getOption("autobackup"))
        vlayout1.addWidget(self.auto_cb)

        # group the directory and autobackup widgets
        bw1 = BorderedWidget(self)
        bw1.setLayout(vlayout1)
        bw1.addTitle("Backup Options")
        vlayout.addWidget(bw1)

        # create the delimiter widget
        r = QHBoxLayout()
        lbl = QLabel(self, text="Delimiter:")
        self.delimiter_le = QLineEdit(
            self, 
            text=self.series.getOption("backup_delimiter")
        )
        # resizeLineEdit(self.delimiter_le, "000")
        self.delimiter_le.textChanged.connect(self.updateWidgets)
        r.addWidget(lbl)
        r.addWidget(self.delimiter_le)

        vlayout2.addLayout(r)

        self.widgets = {}

        widget_info = [
            ("prefix", ""), # updated later
            ("series", self.series.code),
            ("filename", self.series.name),
            ("date", ""),  # updated later
            ("time", ""),  # updated later
            ("user", self.series.user),
            ("suffix", "") # updated later
        ]

        self.save_name_lbl = QLabel(self)

        # create the widgets for each field
        for k, v in widget_info:
            r = QHBoxLayout()
            cb = QCheckBox(self)
            opt_heading = "Series" if k == "name" else k.title()
            cb.setText(opt_heading)
            cb.setChecked(series.getOption(f"backup_{k}"))
            cb.stateChanged.connect(self.updateWidgets)
            r.addWidget(cb)

            if v:
                w = QLabel(self, text=v)
                r.addWidget(w)
                r.addStretch()
            else:
                w = QLineEdit(self, text=v)
                w.textChanged.connect(self.updateWidgets)
                w.setText(self.series.getOption(f"backup_{k}_str"))
                r.addWidget(w)
                if k in ("date", "time"):
                    bttn = QPushButton(self, text="?")
                    bttn.clicked.connect(openCodesLink)
                    tip = date_tip if k == "date" else time_tip
                    bttn.setToolTip(tip)
                    r.addWidget(bttn)

            vlayout2.addLayout(r)
            self.widgets[k] = (cb, w)

        # display name
        vlayout2.addSpacing(10)
        vlayout2.addWidget(QLabel(self, text="Example Backup File Name:"))
        vlayout2.addWidget(self.save_name_lbl)

        # group the naming widgets
        bw2 = BorderedWidget(self)
        bw2.setLayout(vlayout2)
        bw2.addTitle("Backup Naming")
        vlayout.addWidget(bw2)

        if include_confirm:
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
        for name, (cb, w) in self.widgets.items():
            if cb.isChecked() and w.text():
                if name in ("date", "time"):
                    text = self.now.strftime(w.text())
                else:
                    text = w.text()
                l.append(text.replace(" ", dl))
        self.save_name_lbl.setText(dl.join(l) + ".jser")
    
    def accept(self, close=True):
        """Overwritten from parent class.
        
            Params:
                close (bool): True if close when successful
        """
        # bdir = self.dir_widget.text()
        # if not os.path.isdir(bdir):
        #     notify("Please enter a valid directory.")
        #     return False
        if close: super().accept()
        return True
    
    def set(self):
        """Set the series options with the requested backup data"""
        if self.accept():
            # set the series options
            self.series.setOption("autobackup", self.auto_cb.isChecked())
            self.series.setOption("backup_dir", self.dir_widget.text())
            for name, (cb, w) in self.widgets.items():
                self.series.setOption(
                    f"backup_{name}",
                    cb.isChecked()
                )
                if name in ("date", "time", "prefix", "suffix"):
                    self.series.setOption(
                        f"backup_{name}_str", 
                        w.text()
                    )
            self.series.setOption(
                "backup_delimiter",
                self.delimiter_le.text()
            )
    
    def exec(self):
        "Run the dialog."
        confirmed = super().exec()
        if confirmed:
            self.set()
            return True
        else:
            return False

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
