"""Application UI operations.

Shortcuts, trace palette copying/setting, duplicate traces, series options, username, help, etc.
"""

import webbrowser

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication, QInputDialog

from PyReconstruct.modules.gui.utils import notify
from PyReconstruct.modules.gui.dialog import ShortcutsDialog, AllOptionsDialog, QuickDialog
from PyReconstruct.modules.gui.popup import AboutWidget, TextWidget


class UIOperations:

    def seriesModified(self, modified=True):
        """Change the title of the window reflect modifications."""
        # check for welcome series
        if self.series.isWelcomeSeries():
            self.setWindowTitle("PyReconstruct")
            return
        
        if modified:
            self.setWindowTitle(self.series.name + "*")
        else:
            self.setWindowTitle(self.series.name)
        self.series.modified = modified

        if self.field:
            self.checkActions()
    
    def createShortcuts(self):
        """Create shortcuts that are NOT included in any menus."""
        # domain translate motions
        shortcuts = [
            ("Backspace", self.backspace),

            ("Ctrl+Left", lambda : self.translate("left", "small")),
            ("Left", lambda : self.translate("left", "med")),
            ("Shift+Left", lambda : self.translate("left", "big")),
            ("Ctrl+Right", lambda : self.translate("right", "small")),
            ("Right", lambda : self.translate("right", "med")),
            ("Shift+Right", lambda : self.translate("right", "big")),
            ("Ctrl+Up", lambda : self.translate("up", "small")),
            ("Up", lambda : self.translate("up", "med")),
            ("Shift+Up", lambda : self.translate("up", "big")),
            ("Ctrl+Down", lambda : self.translate("down", "small")),
            ("Down", lambda : self.translate("down", "med")),
            ("Shift+Down", lambda : self.translate("down", "big")),

            ("Ctrl+Shift+Left", self.field.rotateTform),
            ("Ctrl+Shift+Right", lambda : self.field.rotateTform(cc=False)),

            ("F1", lambda : self.field.scaleTform(sx=1.005)),
            ("Shift+F1", lambda : self.field.scaleTform(sx=0.995)),
            ("F2", lambda : self.field.scaleTform(sy=1.005)),
            ("Shift+F2", lambda : self.field.scaleTform(sy=0.995)),
            ("F3", lambda : self.field.shearTform(sx=0.005)),
            ("Shift+F3", lambda : self.field.shearTform(sx=-0.005)),
            ("F4", lambda : self.field.shearTform(sy=0.005)),
            ("Shift+F4", lambda : self.field.shearTform(sy=-0.005)),
        ]

        for kbd, act in shortcuts:
            self.addAction("", kbd, act)
    
    def createPaletteShortcuts(self):
        """Create shortcuts associate with the mouse palette."""
        # trace palette shortcuts (1-20)
        trace_shortcuts = []
        
        for i in range(1, 21):
            sc_str = ""
            if (i-1) // 10 > 0:
                sc_str += "Shift+"
            sc_str += str(i % 10)
            s_switch = (
                sc_str,
                lambda pos=i-1 : self.mouse_palette.activatePaletteButton(pos)
            )
            s_modify = (
                "Ctrl+" + sc_str,
                lambda pos=i-1 : self.mouse_palette.modifyPaletteButton(pos)
            )
            trace_shortcuts.append(s_switch)
            trace_shortcuts.append(s_modify)
        
        for kbd, act in trace_shortcuts:
            self.addAction("", kbd, act)

        
        # mouse mode shortcuts (F1-F8)
        mode_shortcuts = [
            ("usepointer_act", lambda : self.mouse_palette.activateModeButton("Pointer")),
            ("usepanzoom_act", lambda : self.mouse_palette.activateModeButton("Pan/Zoom")),
            ("useknife_act", lambda : self.mouse_palette.activateModeButton("Knife")),
            ("usectrace_act", lambda : self.mouse_palette.activateModeButton("Closed Trace")),
            ("useotrace_act", lambda : self.mouse_palette.activateModeButton("Open Trace")),
            ("usestamp_act", lambda : self.mouse_palette.activateModeButton("Stamp")),
            ("usegrid_act", lambda : self.mouse_palette.activateModeButton("Grid")),
            ("useflag_act", lambda : self.mouse_palette.activateModeButton("Flag")),
            ("usehost_act", lambda : self.mouse_palette.activateModeButton("Host")),
        ]
  
        for act_name, act in mode_shortcuts:
            setattr(
                self, 
                act_name, 
                self.addAction("", self.series.getOption(act_name), act)
            )
    
    def displayShortcuts(self):
        """Display the shortcuts."""
        response, confirmed = ShortcutsDialog(self, self.series).exec()
        if not confirmed:
            return
        
        self.resetShortcuts(response)

    def resetShortcuts(self, shortcuts_dict : dict = None):
        """Reset the shortcuts for the window.
        
            Params:
                shortcuts_dict: the action name : shortcut pairs (will use series opts if not provided)
        """
        if shortcuts_dict is None:
            shortcuts_dict = {}
            for k in Series.qsettings_defaults:
                if k.endswith("_act") and getattr(self, k):
                    shortcuts_dict[k] = self.series.getOption(k)
        
        for act_name, kbd in shortcuts_dict.items():
            getattr(self, act_name).setShortcut(kbd)
            self.series.setOption(act_name, kbd)
    
    def resetTracePalette(self):
        """Reset the trace palette to default traces."""
        self.mouse_palette.resetPalette()
        self.saveAllData()
        self.seriesModified()
    
    def pasteAttributesToPalette(self, use_shape=False):
        """Paste the attributes from the first clipboard trace to the selected palette button."""
        
        if self.field.focus_mode:
            return
        
        if not self.field.clipboard and not self.field.section.selected_traces:
            return
        
        elif not self.field.clipboard:
            trace = self.field.section.selected_traces[0]
            
        else:
            trace = self.field.clipboard[0]
            
        self.mouse_palette.pasteAttributesToButton(trace, use_shape)
    
    def setPaletteButtonFromObj(self, name : str):
        """Set the name for the selected palette button.
        
        (Used by the object list)
        
            Params:
                name (str): the name to set the button
        """
        # get the first instance of the object
        first_section = self.series.data.getStart(name)
        if first_section is None:
            return
        
        section = self.series.loadSection(first_section)
        obj_trace = section.contours[name][0].copy()

        pname, i = self.series.palette_index
        trace = self.series.palette_traces[pname][i]
        trace.name = name
        trace.color = obj_trace.color
        trace.fill_mode = obj_trace.fill_mode
        self.mouse_palette.modifyPaletteButton(i, trace)
    
    def allOptions(self):
        """Display the series options dialog."""
        confirmed = AllOptionsDialog(self, self.series).exec()
        if confirmed:
            self.field.generateView()
            self.mouse_palette.reset()
            self.setTheme(self.series.getOption("theme"))
    
    def changeUsername(self, new_name : str = None):
        """Edit the login name used to track history.
        
            Params:
                new_name (str): the new username
        """
        if new_name is None:
            new_name, confirmed = QInputDialog.getText(
                self,
                "Username",
                "Enter your username:",
                text=QSettings("KHLab", "PyReconstruct").value("username", self.series.user),
            )
            if not confirmed or not new_name:
                return
        
        QSettings("KHLab", "PyReconstruct").setValue("username", new_name)
        self.series.user = new_name

        self.notifyNewEditor()
    
    def openWebsite(self, site):
        """Open website in user's browser."""
        webbrowser.open(site)

    def copyCommit(self):
        """Copy current commit or repo."""
        clipboard = QApplication.clipboard()
        clipboard.setText(repo_info["commit"])

    def displayAbout(self):
        """Display the widget display information about the series."""
        # update the editors
        editors = self.series.getEditorsFromHistory()
        self.series.editors = self.series.editors.union(editors)

        AboutWidget(self, self.series)
    
    def notifyNewEditor(self):
        """Provide any relevant notifications to new editors."""
        if (
            not self.series.isWelcomeSeries() and
            self.series.user not in self.series.editors and
            len(self.series.getAlignments()) > 2
        ):
            notify(
                "Note: this series has multiple alignments.\n" + 
                f"Press {self.series.getOption('changealignment_act')} to view"
            )
    
    def setTheme(self, new_theme=None):
        """Change the theme."""
        if new_theme is None:
            theme = self.series.getOption("theme")
            structure = [
                ["Theme:"],
                [("radio", ("Default", theme=="default"), ("Dark", theme=="qdark"))]
            ]
            response, confirmed = QuickDialog.get(
                self, structure, "Theme"
            )
            if not confirmed:
                return
            
            if response[0][0][1]:
                new_theme = "default"
            elif response[0][1][1]:
                new_theme = "qdark"
            else:
                return
        
        app = QApplication.instance()
        
        if new_theme == "default":
            self.series.setOption("theme", "default")
            app.setStyleSheet("")
            app.setPalette(app.style().standardPalette())

        elif new_theme == "qdark":
            
            try:
                import qdarkstyle
            except:
                notify("Unable to import dark theme.")
                return
            
            self.series.setOption("theme", "qdark")
            
            app.setStyleSheet(
                qdarkstyle.load_stylesheet_pyside6() + 
                qdark_addon
            )
    
    def addToRecentSeries(self, series_fp : str = None):
        """Add a series to the recently opened series list."""
        if series_fp is None:
            if self.series.isWelcomeSeries():
                return
            series_fp = self.series.jser_fp
        
        opened = self.series.getOption("recently_opened_series")

        # remove redundant filepaths
        while series_fp in opened:
            opened.remove(series_fp)
        
        opened.insert(0, series_fp)

        # limit to ten items
        if len(opened) > 10:
            opened.pop()
                
        self.series.setOption("recently_opened_series", opened)
    
    def deleteDuplicateTraces(self):
        """Remove all duplicate traces from the series."""
        self.saveAllData()

        structure = [
            ["Overlap threshold:", ("float", 0.95, (0, 1))],
            [("check", ("check locked traces", True))]
        ]
        response, confirmed = QuickDialog.get(self, structure, "Remove duplicate traces")
        if not confirmed:
            return
        threshold = response[0]
        include_locked = response[1][0][1]
        
        removed = self.series.deleteDuplicateTraces(threshold, include_locked, self.field.series_states)

        if removed:
            message = "The following duplicate traces were removed:"
            for snum in removed:
                message += f"\nSection {snum}: " + ", ".join(removed[snum])
            TextWidget(self, message, title="Removed Traces")
        else:
            notify("No duplicate traces found.")

        self.field.reload()
        self.seriesModified(True)

    def editSeriesCodePattern(self):
        """Edit the regex pattern used to automatically detect series codes."""
        response, confirmed = QInputDialog.getText(
            self,
            "Series Code Pattern",
            "Enter the regex pattern for series codes:",
            text=self.series.getOption("series_code_pattern")
        )
        if not confirmed:
            return
        
        self.series.setOption("series_code_pattern", response)
    
    def setSeriesCode(self, cancelable=True):
        """Set the series code (ensure that user enters a valid series code)."""
        code_is_valid = False
        while not code_is_valid:
            structure = [
                ["The series code is a unique set of characters that identifies\n" + 
                "a specific series, regardless of the file name."],
                [" "],
                ["Series code:", (True, "text", self.series.code)]
            ]
            response, confirmed = QuickDialog.get(self, structure, "Series Code", cancelable=cancelable)
            if confirmed:
                self.series.code = response[0]
            
            code_is_valid = bool(self.series.code)

            if not code_is_valid:
                notify("Please enter a code for the series.")
    
