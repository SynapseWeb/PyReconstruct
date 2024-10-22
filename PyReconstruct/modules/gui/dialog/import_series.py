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
    QTabWidget,
    QComboBox,
)
from PySide6.QtCore import Qt

from .helper import BrowseWidget, MultiInput, BorderedWidget, RadioButtonGroup, resizeLineEdit
from .quick_dialog import getLayout
from PyReconstruct.modules.gui.utils import notify
from PyReconstruct.modules.datatypes import Series


tip_overlap = """Overlap fraction above which two traces are
considered "functional duplicates" during import.

When two users trace the same object, the traces
may both appear valid by eye but differ slightly
in their points. We refer to multiple valid, but
non-identical traces for a single object as
functional duplicates.

Setting the overlap threshold to 1.0 will instruct
PyReconstruct to consider traces duplicates only
if their points match perfectly. This is in most
cases too strict. A value of 0.95 is usually
sufficient to identify overlapping, non-identical
traces of a single object that are all valid.

The overlap fraction is also known as the Jaccard
index and is calculated as the intersection of the
two traces divided by their union."""


tip_history = """When this option is checked, contours that have NOT
been modified since the divergence of the two series
will be ignored."""


tip_conflicts = """When this option is checked, traces that have not been
resolved through overlap or history will be flagged."""


def addTip(widget : QWidget, tip_text : str):
    """Add a tip to a widget with text.
    
        Params:
            widget (QWidget): the widget to modify
            tip_text (str): the tool tip to display
    """
    widget.setText(widget.text() + "ˀ")
    widget.setToolTip(tip_text)
    widget.setToolTipDuration(60000)


class ImportSeriesDialog(QDialog):

    def __init__(self, parent : QWidget, series : Series, other : Series):
        """Create an import from other series dialog.
        
            Params:
                parent (QWidget): the parent widget
                series (Series): the current series obj
                other (Series): the series importing from
        """
        super().__init__(parent)
        self.series = series
        self.other = other

        vlayout = QVBoxLayout()
        vlayout.setSpacing(10)

        ## Create import widgets
        import_widgets = []
        self.responses = {}

        ## Trace tab
        import_widgets.append(("traces", ImportTracesWidget(self, series, other)))

        # ## Group tab
        # structure = [
        #     ["Restrict to importing object in groups:"],
        #     [("multicombo", list(other.object_groups.getGroupList()), [], False)]
        # ]
        
        # import_widgets.append(("groups", ImportWidget(self, structure)))

        ## Z-trace tab
        structure = [
            ["Z-trace regex filters:"],
            [("multicombo", list(other.ztraces.keys()), [], False)],
            [("check", ("Import z-trace groups", True))]
        ]

        import_widgets.append(("z-traces", ImportWidget(self, structure)))

        ## Flags tab
        sections = list(series.sections.keys())
        
        structure = [
            [
                "From section",
                ("int", min(sections), sections),
                "to",
                ("int", max(sections), sections),
                " "
            ]
        ]

        import_widgets.append(("flags", ImportWidget(self, structure)))

        ## Obj attrs tab
        structure = [
            [("check",
              ("Object groups", False),
              ("Hosts", False),
              ("User columns ", False),
              ("Z-trace groups", False),
              ("Misc object attributes\n(3D settings, alignments, curation, etc.)", False),
            )]
        ]

        import_widgets.append(("attributes", ImportWidget(self, structure)))

        ## Alignments tab
        import_widgets.append((
            "alignments",
            MultiImportAs(
                self, 
                other.alignments, 
                series.alignments, 
                "alignment"
            )
        ))

        ## Palettes tab
        import_widgets.append((
            "palettes",
            MultiImportAs(
                self, 
                list(other.palette_traces.keys()), 
                list(series.palette_traces.keys()), 
                "palette"
            )
        ))

        ## BC profiles tab
        import_widgets.append((
            "brightness/contrast profiles",
            MultiImportAs(
                self, 
                other.bc_profiles, 
                series.bc_profiles, 
                "brightness/contrast profile"
            )
        ))

        ## Tabs for different import widgets
        tabs = QTabWidget(self)
        for name, widget in import_widgets:
            vl = QVBoxLayout()
            # checkbox for enabling import
            cb = QCheckBox(f"Import {name}", self)
            cb.setChecked(False)
            widget.setEnabled(False)
            cb.stateChanged.connect(widget.setEnabled)
            # add widgets to layout
            vl.addWidget(cb)
            vl.addWidget(widget)
            vl.addStretch()
            container = QWidget(self)
            container.setLayout(vl)
            # add tab to overall structure
            tabs.addTab(container, name.capitalize())
        vlayout.addWidget(tabs)

        self.import_widgets = dict(import_widgets)
        
        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        buttonbox = QDialogButtonBox(QBtn)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)
        vlayout.addWidget(buttonbox)

        self.setLayout(vlayout)
    
    def accept(self):
        """Run when user clicks OK."""
        self.responses = {}
        
        for name, import_widget in self.import_widgets.items():
            
            import_widget : QWidget
            
            if not import_widget.isEnabled():
                continue
            
            response, confirmed = import_widget.getResponse()

            if not confirmed:
                return
            
            self.responses[name] = response

        super().accept()

    def exec(self):
        """Run the dialog."""
        confirmed = super().exec()
        if confirmed:
            return self.responses, True
        else:
            return None, False


class ImportTracesWidget(QWidget):

    def __init__(self, parent, series : Series, other : Series):
        """Create an import traces widget.
        
            Params:
                parent (QWidget): the parent widget
                series (Series): the series object
                other (Series): the series importing from
        """
        super().__init__(parent)
        self.series = series

        vlayout = QVBoxLayout()
        vlayout.setSpacing(10)
        
        top_hlayout = QHBoxLayout()
        top_vlayout1 = QVBoxLayout()
        top_vlayout2 = QVBoxLayout()

        ## Section range
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

        ## Check series histories checkbox
        self.check_histories = QCheckBox(self, text="Check series histories")
        addTip(self.check_histories, tip_history)
        top_vlayout1.addSpacing(10)
        top_vlayout1.addWidget(self.check_histories)

        ## Flag conflicts checkbox
        self.flag_conflicts = QCheckBox(self, text="Flag conflicts")
        addTip(self.flag_conflicts, tip_conflicts)
        self.flag_conflicts.setChecked(True)
        top_vlayout1.addSpacing(5)
        top_vlayout1.addWidget(self.flag_conflicts)

        ## Import object attrs checkbox
        self.import_attrs = QCheckBox(self, text="Import object attributes")
        self.import_attrs.setChecked(True)
        top_vlayout1.addSpacing(5)
        top_vlayout1.addWidget(self.import_attrs)

        ## Object regex filters
        top_vlayout2.addWidget(QLabel(self, text="Object regex filters:"))
        self.regex_filters = MultiInput(
            self,
            entries=[],
            combo=True,
            combo_items=list(other.data["objects"].keys()),
            restrict_to_opts=False
        )
        top_vlayout2.addWidget(self.regex_filters)

        top_vlayout2.addWidget(
            QLabel(self, text="Restrict to obj groups:")
        )

        self.group_filters = MultiInput(
            self,
            entries=[],
            combo=True,
            combo_items=other.object_groups.getGroupList(),
            restrict_to_opts=False
        )

        top_vlayout2.addWidget(self.group_filters)

        ## Arrange layouts for top of dialog
        
        w1 = BorderedWidget(self)
        w1.setLayout(top_vlayout1)
        top_hlayout.addWidget(w1)
        
        w2 = BorderedWidget(self)
        w2.setLayout(top_vlayout2)
        top_hlayout.addWidget(w2)

        vlayout.addLayout(top_hlayout)

        ## Create container widget for overlap-related parameters
        container = BorderedWidget(self)
        cvlayout = QVBoxLayout()

        ## Overlap threshold text
        hlayout = QHBoxLayout()
        lbl = QLabel(self ,text="Overlap threshold:")
        addTip(lbl, tip_overlap)
        hlayout.addWidget(lbl)
        self.overlap_threshold = QLabel(self)
        hlayout.addWidget(self.overlap_threshold)
        hlayout.addStretch()
        cvlayout.addLayout(hlayout)

        ## Overlap threshold slider
        slider = QSlider(Qt.Horizontal, self)
        slider.setMinimum(0)
        slider.setMaximum(100)
        slider.valueChanged.connect(self.setOverlapThreshold)
        slider.setValue(50)
        cvlayout.addWidget(slider)

        ## Radio button options
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
        
        # QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        # buttonbox = QDialogButtonBox(QBtn)
        # buttonbox.accepted.connect(self.accept)
        # buttonbox.rejected.connect(self.reject)
        # vlayout.addWidget(buttonbox)

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
        # if not os.path.isfile(self.series_fp.text()):
        #     notify("Please enter a valid series jser.")
        #     return
        smin = self.smin.text()
        smax = self.smax.text()
        if not smin.isnumeric() or not smax.isnumeric():
            notify("Please enter a valid number.")
            return False
        if (
            not int(smin) in self.series.sections or
            not int(smax) in self.series.sections
        ):
            notify("Please enter a valid section number.")
            return False

        return True
    
    def getResponse(self):
        """Get the response from the user."""
        if self.accept():

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

            response = (
                (int(self.smin.text()), int(self.smax.text()) + 1),
                self.regex_filters.getEntries(),
                self.group_filters.getEntries(),
                float(self.overlap_threshold.text()),
                self.flag_conflicts.isChecked(),
                self.check_histories.isChecked(),
                self.import_attrs.isChecked(),
                keep_above,
                keep_below,
            )

            return response, True
        
        else:
            
            return None, False


class ImportWidget(QWidget):

    def __init__(self, parent, structure):
        """Create the import widget.
        
            Params:
                parent (QWidget): the parent for this widget
                series (Sereis): the series obj
                structure (list): the structure of the widget
        """
        super().__init__(parent)

        vlayout, self.inputs = getLayout(self, structure)
        self.setLayout(vlayout)
        self.responses = []
    
    def accept(self):
        """Called when OK is pressed."""
        for input in self.inputs:
            response, is_valid = input.getResponse()
            if not is_valid:
                return False
            else:
                self.responses.append(response)
        return True

    def getResponse(self):
        """Get the response from the user."""
        if self.accept():
            return tuple(self.responses), True
        else:
            return None, False


class ImportAs(QWidget):

    def __init__(self, parent=None, combo_items=[]):
        """Create the import __ as __ widget."""
        super().__init__(parent)

        # set up the inputs
        self.input_1 = QComboBox(self)
        self.input_1.addItems(combo_items)
        self.input_2 = QLineEdit("", self)

        # set up the layout
        hlayout = QHBoxLayout()
        hlayout.addWidget(QLabel("Import", self))
        hlayout.addWidget(self.input_1)
        hlayout.addWidget(QLabel("as", self))
        hlayout.addWidget(self.input_2)

        self.setLayout(hlayout)
    
    def getResponse(self):
        """Get the user response."""
        return (
            self.input_1.currentText(),
            self.input_2.text()
        )


class MultiImportAs(QWidget):

    def __init__(self, parent : QWidget, other_items, self_items, name : str):
        """Create the multi line edit widget."""
        super().__init__(parent)

        vbl = QVBoxLayout()
        self.input_layout = QVBoxLayout()
        self.other_items = other_items
        self.self_items = self_items
        self.name = name

        # create the inputs
        self.inputs = []
        w = ImportAs(self, self.other_items)
        self.input_layout.addWidget(w)
        self.inputs.append(w)
        vbl.addLayout(self.input_layout)

        # create the add/remove buttons
        ar_row = QHBoxLayout()
        ar_row.addStretch(10)
        remove = QPushButton(self, text="-")
        remove.clicked.connect(self.remove)
        ar_row.addWidget(remove)
        add = QPushButton(self, text="+")
        add.clicked.connect(self.add)
        ar_row.addWidget(add)
        vbl.addLayout(ar_row)

        self.setLayout(vbl)
    
    def add(self):
        """Add a line edit row to the field."""
        w = ImportAs(self, self.other_items)
        self.input_layout.addWidget(w)
        self.inputs.append(w)
    
    def remove(self):
        """Remove a line edit row from the field."""
        if self.inputs:
            self.inputs.pop().deleteLater()
            self.adjustSize()
    
    def getEntries(self):
        """Get the strings input by the user."""
        l = []
        for w in self.inputs:
            l.append(w.getResponse())
        return l
    
    def accept(self):
        """Called when user presses OK"""
        entries = self.getEntries()
        if not entries:
            notify("Please select an option to import.")
            return False
        new_names = set()
        for name, new_name in entries:
            if name not in self.other_items:
                notify(f"Please select a valid {self.name}.")
                return False
            if not new_name:
                notify("Please enter a valid name.")
                return False
            if new_name in self.self_items:
                notify(f"{self.name.capitalize()} name already exists in current series.")
                return False
            if new_name in new_names:
                notify(f"Cannot import multiple {self.name}s as the same name.")
                return False
            new_names.add(new_name)
        
        return True
    
    def getResponse(self):
        """Get the user response"""
        if self.accept():
            return self.getEntries(), True
        else:
            return None, False
