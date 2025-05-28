from PySide6.QtWidgets import (
    QLabel, 
    QWidget, 
    QDialog, 
    QGridLayout, 
    QPushButton,
    QDialogButtonBox,
    QVBoxLayout,
    QScrollArea,
    QKeySequenceEdit,
)
from PySide6.QtGui import QKeySequence, QAction, QShortcut
from PySide6.QtCore import Qt

from PyReconstruct.modules.datatypes import Series
from PyReconstruct.modules.gui.utils import notify


class ShortcutsDialog(QDialog):

    def __init__(self, mainwindow : QWidget, series : Series):
        """Create a shortcuts dialog.
        
            Params:
                series (Series): the current sereis being used
        """
        super().__init__(mainwindow)
        self.mainwindow = mainwindow
        self.series = series

        grid = QGridLayout()
        self.act_widgets = {}

        for row, item in enumerate(help_shortcuts):
            if item is None:  # spacer
                grid.addWidget(QLabel(self, text=" "), row, 0)
            elif type(item) is str:  # header
                l = QLabel(self, text=item)
                f = l.font()
                f.setBold(True)
                l.setFont(f)
                grid.addWidget(l, row, 0)
            else:  # shortcut item
                sc, desc = tuple(item)
                if sc.endswith("_act") and getattr(self.mainwindow, sc):
                    w = QKeySequenceEdit(self.series.getOption(sc), self)
                    w.setClearButtonEnabled(True)
                    self.act_widgets[sc] = w
                else:
                    w = QLabel(self, text=sc)
                grid.addWidget(w, row, 0)
                grid.addWidget(QLabel(self, text=desc), row, 1)
        
        QBtn = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        buttonbox = QDialogButtonBox(QBtn)
        buttonbox.accepted.connect(self.accept)
        buttonbox.rejected.connect(self.reject)

        reset_defaults_button = QPushButton("Reset Defaults")
        reset_defaults_button.clicked.connect(self.resetDefaults)
        buttonbox.addButton(reset_defaults_button, QDialogButtonBox.ResetRole)

        qsa = QScrollArea(self)
        w = QWidget(self)
        w.setLayout(grid)
        qsa.setWidget(w)

        vlayout = QVBoxLayout()
        vlayout.setSpacing(10)
        vlayout.addWidget(qsa)
        vlayout.addWidget(buttonbox)

        self.setLayout(vlayout)
    
    def resetDefaults(self):
        """Reset the defaults for all fields."""
        for act, w in self.act_widgets.items():
            w.setKeySequence(self.series.getOption(act))
    
    def accept(self):
        """Called when user accepts the dialog."""
        # gather the modifiable actions
        modifiable_actions = []
        for act_name in self.act_widgets:
            modifiable_actions.append(getattr(self.mainwindow, act_name))
        
        # gather the static key sequences
        keyseqs = []
        for act in self.mainwindow.actions():
            if act.shortcut().toString() and act not in modifiable_actions:
                keyseqs.append(act.shortcut())
        
        # compare with the user-entered key sequences
        for input in self.act_widgets.values():
            ks = input.keySequence()
            if not ks.toString():
                continue
            if ks in keyseqs:
                notify(f"The keyboard shortcut '{ks.toString()}' is used more than once.")
                return
            keyseqs.append(ks)

        return super().accept()
    
    def exec(self):
        """Run the dialog."""
        confirmed = super().exec()

        if confirmed:
            shortcuts_dict = {}
            for act_name, keyseq in self.act_widgets.items():
                shortcuts_dict[act_name] = keyseq.keySequence().toString()
            return shortcuts_dict, True
        else:
            return None, False


def getStaticShortcuts(w : QWidget) -> list[QKeySequence]:
    """Get static shortcuts of the mainwindow."""
    keyseqs : list[QKeySequence] = []
    # get all of the static actions
    for aname in dir(w):
        if (
            aname.endswith("_act") and 
            aname not in Series.qsettings_defaults and
            type(getattr(w, aname)) is QAction
        ):
            qact : QAction = getattr(w, aname)
            keyseqs.append(qact.shortcut())
    # get all of the static shortcuts
    for sc in w.non_action_shortcuts:
        keyseqs.append(sc.key())
    
    return keyseqs
            

help_shortcuts = [
    "General",
    ("Delete/Backspace", "Delete selected traces"),
    ("", "Remove last point when polyline tracing or using scissors."),
    ("", "Delete selected entry in lists"),
    ("? (Shift+/)", "Display keyboard shortcuts"),
    ("alloptions_act", "View all options"),
    ("Page Up", "Display the next (higher) section"),
    ("Page Down", "Display the preceding (lower) section"),
    ("flicker_act", "Switch between current and last viewed section"),
    None,
    "View",
    ("focus_act", "Toggle focus mode"),
    ("hideall_act", "Toggle hide all traces (regardless of trace's hide status)"),
    ("showall_act", "Toggle show all traces (regardless of trace's hide status)"),
    ("hideimage_act", "Toggle hide images"),
    ("decbr_act", "Decrease brightness"),
    ("incbr_act", "Increase brightness"),
    ("deccon_act", "Decrease contrast"),
    ("inccon_act", "Increase contrast"),
    ("blend_act", "Blend current and last viwed section"),
    ("homeview_act", "Set view to image"),
    None,
    "Field Interactions",
    ("selectall_act", "Select all traces on section"),
    ("deselect_act", "Deselect all traces on section"),
    ("edittrace_act", "Edit attributes of selected trace(s)"),
    ("mergetraces_act", "Merge selected traces"),
    ("mergeobjects_act", "Merge attributes of selected traces"),
    ("hidetraces_act", "Hide selected traces"),
    ("unhideall_act", "Unhide all hidden traces on current section"),
    ("pastetopalette_act", "Modify current palette button to match attributes of first selected trace"),
    ("pastetopalettewithshape_act", "Modify current palette button to match attributes and shape of first selected trace"),
    ("unlocksection_act", "Unlock current section"),
    ("changetform_act", "Modify transform on current section"),
    ("sethosts_act", "Set host(s) for selected trace(s)"),
    None,
    "Edit",
    ("undo_act", "Undo"),
    ("redo_act", "Redo"),
    ("copy_act", "Copy selected traces to clipboard"),
    ("cut_act", "Cut selected traces to clipboard"),
    ("paste_act", "Paste clipboard traces into section"),
    ("pasteattributes_act", "Apply attributes of copied traces to selected trace(s)"),
    None,
    "Navigate",
    ("findobjectfirst_act", "Find first instance of a trace in the series"),
    ("findcontour_act", "Find a trace on the current section"),
    ("goto_act", "Go to a specific section number"),
    None,
    "File",
    ("open_act", "Open a series file"),
    ("save_act", "Save"),
    ("manualbackup_act", "Backup series"),
    ("newfromimages_act", "New series"),
    ("restart_act", "Restart"),
    ("quit_act", "Quit"),
    None,
    "Lists",
    ("objectlist_act", "Open Object List"),
    ("togglecuration_act", "Toggle curation columns in object list"),
    ("tracelist_act", "Open Trace List"),
    ("ztracelist_act", "Open Ztrace List"),
    ("sectionlist_act", "Open Section List"),
    ("flaglist_act", "Open Flag List"),
    ("changealignment_act", "Switch/modify alignments"),
    None,
    "Trace Palette",
    ("#, Shift+#", "Select a trace on the palette"),
    ("Ctrl+#, Ctrl+Shift+#", "Edit attributes of a single trace on the palette"),
    ("modifytracepalette_act", "Switch/modify palettes"),
    ("incpaletteup_act", "Increment palette {#} up"),
    ("incpalettedown_act", "Increment palette {#} down"),
    None,
    "Movements",
    ("Left/Right/Up/Down", "Translate selected traces or image (when no trace selected)"),
    ("Ctrl+Left/Right/Up/Down", "Translate traces or image by small step"),
    ("Shift+Left/Right/Up/Down", "Translate trace or image by large step"),
    ("Ctrl+Shift+Left/Right/Up/Down", "Rotate image around the mouse"),
    ("F1, Shift+F1, F2, Shift+F2", "Scale image in X and Y"),
    ("F3, Shift+F3, F4, Shift+F4", "Shear image in X and Y"),
    None,
    "Tool Palette",
    ("usepointer_act", "Use pointer tool"),
    ("usepanzoom_act", "Use pan/zoom tool"),
    ("useknife_act", "Use knife tool"),
    ("usectrace_act", "Use closed trace tool"),
    ("useotrace_act", "Use open trace tool"),
    ("usestamp_act", "Use stamp tool"),
    ("usegrid_act", "Use grid tool"),
    ("useflag_act", "Use flag tool"),
    ("usehost_act", "Use host tool"),
    None,
    "3D Scene:",
    ("? (Shift+/)", "Display shortcuts in 3D scene"),
]
