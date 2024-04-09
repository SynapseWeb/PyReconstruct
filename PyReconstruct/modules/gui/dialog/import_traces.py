import os

from PySide6.QtWidgets import (
    QApplication,
    QWidget, 
    QDialog, 
    QDialogButtonBox, 
    QHBoxLayout, 
    QLabel, 
    QVBoxLayout, 
    QTextEdit,
    QPushButton,
    QStyle,
    QLineEdit,
    QScrollArea,
    QApplication,
    QCheckBox,
    QSlider,
)
from PySide6.QtCore import Qt

from .helper import BrowseWidget, MultiLineEdit, BorderedWidget, RadioButtonGroup, resizeLineEdit
from PyReconstruct.modules.gui.utils import notify

class ImportTracesDialog(QDialog):

    def __init__(self, parent : QWidget, series):
        """Create an import traces dialog.
        
            Params:
                parent (QWidget): the parent widget
        """

        super().__init__(parent)
        self.series = series

        self.setWindowTitle("Import Traces")

        vlayout = QVBoxLayout()
        vlayout.setSpacing(10)
        top_hlayout = QHBoxLayout()
        top_vlayout1 = QVBoxLayout()
        top_vlayout2 = QVBoxLayout()

        # series filepath
        hlayout = QHBoxLayout()
        hlayout.addWidget(QLabel(self, text="Series:"))
        self.series_fp = BrowseWidget(self, filter="*.jser")
        hlayout.addWidget(self.series_fp)
        vlayout.addLayout(hlayout)

        # section range
        snums = list(series.sections.keys())
        smin = min(snums)
        smax = max(snums)
        hlayout = QHBoxLayout()
        hlayout.addWidget(QLabel("From section"))
        self.smin = QLineEdit(str(smin), self)
        resizeLineEdit(self.smin, "00000")
        hlayout.addWidget(self.smin)
        hlayout.addWidget(QLabel("to"))
        self.smax = QLineEdit(str(smax), self)
        resizeLineEdit(self.smax, "00000")
        hlayout.addWidget(self.smax)
        hlayout.addStretch()
        top_vlayout1.addLayout(hlayout)

        # check series histories checkbox
        self.check_histories = QCheckBox(self, text="Check series histories")
        addTip(
            self.check_histories,
            "When this option is checked, contours that have NOT\n" +
            "been modified since the divergence of the two series\n" +
            "will be ignored."
        )
        top_vlayout1.addSpacing(10)
        top_vlayout1.addWidget(self.check_histories)

        # flag conflicts checkbox
        self.flag_conflicts = QCheckBox(self, text="Flag conflicts")
        addTip(
            self.flag_conflicts,
            "When this option is checked, traces that have not been\n" +
            "resolved through overlap or history will be flagged."
        )
        self.flag_conflicts.setChecked(True)
        top_vlayout1.addSpacing(10)
        top_vlayout1.addWidget(self.flag_conflicts)

        # object regex filters
        top_vlayout2.addWidget(QLabel(self, text="Object regex filters:"))
        self.regex_filters = MultiLineEdit(self)
        top_vlayout2.addWidget(self.regex_filters)

        # arrange layouts for the top of the dialog
        w1 = BorderedWidget(self)
        w1.setLayout(top_vlayout1)
        top_hlayout.addWidget(w1)
        w2 = BorderedWidget(self)
        w2.setLayout(top_vlayout2)
        top_hlayout.addWidget(w2)
        vlayout.addLayout(top_hlayout)

        # create container widget for overlap-related parameters
        container = BorderedWidget(self)
        cvlayout = QVBoxLayout()

        # overlap threshold text
        hlayout = QHBoxLayout()
        lbl = QLabel(self ,text="Overlap threshold:")
        addTip(
            lbl,
            "The fraction of overlap necessary for two\n" +
            'traces to be considered "functional duplicates."\n\n' +
            "For example, the fraction of overlap between two\n" +
            "identical traces is 1.0.\n\n" +
            "In most cases, an overlap threshold of 0.95 is\n" +
            "sufficient to identify traces that, by eye, appear\n" +
            "to be duplicates but are not exactly identical.\n" +
            "We term these traces functional duplicates."
        )
        hlayout.addWidget(lbl)
        self.overlap_threshold = QLabel(self)
        hlayout.addWidget(self.overlap_threshold)
        hlayout.addStretch()
        cvlayout.addLayout(hlayout)

        # overlap threshold slider
        slider = QSlider(Qt.Horizontal, self)
        slider.setMinimum(0)
        slider.setMaximum(100)
        slider.valueChanged.connect(self.setOverlapThreshold)
        slider.setValue(50)
        cvlayout.addWidget(slider)

        # radio button options
        hlayout = QHBoxLayout()
        vl1 = QVBoxLayout()
        vl1.addWidget(QLabel(
            self,
            text="For traces with overlap BELOW the threshold,\nkeep traces from:"
        ))
        self.below_threshold = RadioButtonGroup(
            self,
            [
                "current series only",
                "importing series only",
                "both series"
            ],
            "both series"
        )
        vl1.addWidget(self.below_threshold)
        hlayout.addLayout(vl1)
        hlayout.addSpacing(10)
        vl2 = QVBoxLayout()
        vl2.addWidget(QLabel(
            self, 
            text="For traces with overlap ABOVE the threshold\n(functional duplicates), keep traces from:"
        ))
        self.above_threshold = RadioButtonGroup(
            self,
            [
                "current series only",
                "importing series only",
                "both series (NOT recommended)"
            ],
            "current series only"
        )
        vl2.addWidget(self.above_threshold)
        hlayout.addLayout(vl2)
        cvlayout.addLayout(hlayout)

        # add container to master layout
        container.setLayout(cvlayout)
        container.addTitle("Differentiate Duplicate and Non-duplicate Traces")
        vlayout.addWidget(container)
        
        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        buttonbox = QDialogButtonBox(QBtn)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        vlayout.addWidget(buttonbox)

        self.setLayout(vlayout)
    
    def setOverlapThreshold(self, value : int):
        """Set the overlap threshold for the displayed label.
        
            Params:
                value (int): the number from 0-100 given by the slider
        """
        min = 0.9
        max = 1
        value = value/100 * (max - min) + min
        self.overlap_threshold.setText(str(round(value, 3)))
    
    def accept(self):
        """Run when user clicks OK."""
        if not os.path.isfile(self.series_fp.text()):
            notify("Please enter a valid series jser.")
            return
        smin = self.smin.text()
        smax = self.smax.text()
        if not smin.isnumeric() or not smax.isnumeric():
            notify("Please enter a valid number.")
            return
        if (
            not int(smin) in self.series.sections or
            not int(smax) in self.series.sections
        ):
            notify("Please enter a valid section number.")
            return
        
        super().accept()

    def exec(self):
        """Run the dialog."""
        confirmed = super().exec()
        if confirmed:
            keep_above = "self"  # establish defaults (redundant)
            keep_below = ""
            i = self.above_threshold.getSelectedIndex()
            if i == 0: keep_above = "self"
            elif i == 1: keep_above = "other"
            elif i == 2: keep_above = ""
            i = self.below_threshold.getSelectedIndex()
            if i == 0: keep_below = "self"
            elif i == 1: keep_below = "other"
            elif i == 2: keep_below = ""

            return (
                self.series_fp.text(),
                (int(self.smin.text()), int(self.smax.text()) + 1),
                self.regex_filters.getEntries(),
                float(self.overlap_threshold.text()),
                self.flag_conflicts.isChecked(),
                self.check_histories.isChecked(),
                keep_above,
                keep_below,
            ), True
        else:
            return None, False

def addTip(widget : QWidget, tip_text : str):
    """Add a tip to a widget with text.
    
        Params:
            widget (QWidget): the widget to modify
            tip_text (str): the tool tip to display
    """
    widget.setText(widget.text() + "ˀ")
    widget.setToolTip(tip_text)
    widget.setToolTipDuration(60000)