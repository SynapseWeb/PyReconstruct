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
    """Get the static shortcuts of the mainwindow."""
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
    ("", "Remove last entered point when polyline tracing or using scissors."),
    ("", "Delete selected entry when using the lists"),
    ("? (Shift+/)", "Display keyboard shortcuts"),
    ("alloptions_act", "View all options"),
    ("Page Up", "Display the next (higher) section"),
    ("Page Down", "Display the preceding (lower) section"),
    ("flicker_act", "Switch back & forth between the current section and last section viewed"),
    None,
    "View",
    ("hideall_act", "Toggle hide all traces, regardless of individual trace hide status"),
    ("showall_act", "Toggle show all traces, regardless of individual trace hide status"),
    ("hideimage_act", "Toggle hide section image"),
    ("decbr_act", "Decrease brightness"),
    ("incbr_act", "Increase brightness"),
    ("deccon_act", "Decrease contrast"),
    ("inccon_act", "Increase contrast"),
    ("blend_act", "Blend the current section with the last section viewed"),
    ("homeview_act", "Set the view to the image"),
    None,
    "Field Interactions",
    ("selectall_act", "Select all traces on a section"),
    ("deselect_act", "Deselect all traces on section"),
    ("edittrace_act", "Edit the attributes of the selected trace(s)"),
    ("mergetraces_act", "Merge the selected traces"),
    ("mergeobjects_act", "Merge the attributes of the selected traces"),
    ("hidetraces_act", "Hide the selected traces"),
    ("unhideall_act", "Unhide all hidden traces on the current section"),
    ("pastetopalette_act", "Modify the current palette button to match attributes of first selected trace"),
    ("pastetopalettewithshape_act", "Modiy the current palette button to match attributes AND shape of first selected trace"),
    ("unlocksection_act", "Unlock the current section"),
    ("changetform_act", "Modify the transform on current section"),
    ("sethosts_act", "Set the host(s) for the selected trace(s)"),
    None,
    "Edit",
    ("undo_act", "Undo"),
    ("redo_act", "Re-do"),
    ("copy_act", "Copy the selected traces onto the clipboard"),
    ("cut_act", "Cut selected traces onto the clipboard"),
    ("paste_act", "Paste clipboard traces into section"),
    ("pasteattributes_act", "Paste attributes of clipboard traces onto selected traces"),
    None,
    "Navigate",
    ("findobjectfirst_act", "Find the first instance of a trace in series"),
    ("findcontour_act", "Find a trace on the current section"),
    ("goto_act", "Go to a specific section number"),
    None,
    "File",
    ("open_act", "Open a series file"),
    ("save_act", "Save"),
    ("manualbackup_act", "Backup series"),
    ("newfromimages_act", "New"),
    ("restart_act", "Restart"),
    ("quit_act", "Quit"),
    None,
    "Lists",
    ("objectlist_act", "Open the Object List"),
    ("togglecuration_act", "Toggle curation columns in object list"),
    ("tracelist_act", "Open the Trace List"),
    ("ztracelist_act", "Open the Ztrace List"),
    ("sectionlist_act", "Open the Section List"),
    ("flaglist_act", "Open the Flag List"),
    ("changealignment_act", "Switch/modify alignments"),
    None,
    "Trace Palette",
    ("#, Shift+#", "Select a trace on the palette"),
    ("Ctrl+#, Ctrl+Shift+#", "Edit attributes for a single trace on the palette"),
    ("modifytracepalette_act", "Switch/modify palettes"),
    ("incpaletteup_act", "Increment palette {#} up"),
    ("incpalettedown_act", "Increment palette {#} down"),
    None,
    "Movements",
    ("Left/Right/Up/Down", "Translate selected traces or image if no trace selected"),
    ("Ctrl+Left/Right/Up/Down", "Translate traces or image a small amount"),
    ("Shift+Left/Right/Up/Down", "Translate trace or image a large amount"),
    ("Ctrl+Shift+Left/Right/Up/Down", "Rotate the image around the mouse"),
    ("F1, Shift+F1, F2, Shift+F2", "Scale image in X and Y"),
    ("F3, Shift+F3, F4, Shift+F4", "Shear image in X and Y"),
    None,
    "Tool Palette",
    ("usepointer_act", "Use the pointer tool"),
    ("usepanzoom_act", "Use the pan/zoom tool"),
    ("useknife_act", "Use the knife tool"),
    ("usectrace_act", "Use the closed trace tool"),
    ("useotrace_act", "Use the open trace tool"),
    ("usestamp_act", "Use the stamp tool"),
    ("usegrid_act", "Use the grid tool"),
    ("useflag_act", "Use the flag tool"),
    ("usehost_act", "Use the host tool"),
    None,
    "3D Scene:",
    ("? (Shift+/)", "Pull up shortcuts for 3D scene"),
]