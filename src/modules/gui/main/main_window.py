import os
import sys
import time
import subprocess

from PySide6.QtWidgets import (
    QMainWindow, 
    QFileDialog,
    QInputDialog, 
    QApplication,
    QMessageBox, 
    QMenu
)
from PySide6.QtGui import (
    QKeySequence,
    QShortcut,
    QPixmap
)
from PySide6.QtCore import Qt

from .field_widget import FieldWidget

from modules.gui.palette import MousePalette, ZarrPalette
from modules.gui.dialog import (
    AlignmentDialog,
    GridDialog,
    CreateZarrDialog,
    AddToZarrDialog,
    TrainDialog,
    SegmentDialog,
    PredictDialog,
    SwiftDialog,
    ImportTransformsDialog,
    SmoothingDialog,
    PointerDialog,
    ClosedTraceDialog
)
from modules.gui.popup import HistoryWidget
from modules.gui.utils import (
    progbar,
    populateMenuBar,
    populateMenu,
    notify,
    saveNotify,
    unsavedNotify,
    getSaveLocation,
    setMainWindow
)
from modules.backend.func import (
    xmlToJSON,
    jsonToXML,
    importTransforms,
    importSwiftTransforms
)
from modules.backend.autoseg import seriesToZarr, seriesToLabels, labelsToObjects
from modules.datatypes import Series, Transform
from modules.constants import welcome_series_dir, assets_dir, img_dir, fd_dir

class MainWindow(QMainWindow):

    def __init__(self, argv):
        """Constructs the skeleton for an empty main window."""
        super().__init__() # initialize QMainWindow
        self.setWindowTitle("PyReconstruct")

        # set the window icon
        pix = QPixmap(os.path.join(img_dir, "PyReconstruct.ico"))
        self.setWindowIcon(pix)

        # set the main window to be slightly less than the size of the monitor
        screen = QApplication.primaryScreen()
        screen_rect = screen.size()
        x = 50
        y = 80
        w = screen_rect.width() - 100
        h = screen_rect.height() - 160
        self.setGeometry(x, y, w, h)

        # misc defaults
        self.series = None
        self.field = None  # placeholder for field
        self.menubar = None
        self.mouse_palette = None  # placeholder for palettes
        self.zarr_palette = None
        self.setMouseTracking(True) # set constant mouse tracking for various mouse modes
        self.is_zooming = False
        self.restart_mainwindow = False

        # create status bar at bottom of window
        self.statusbar = self.statusBar()

        # open the series requested from command line
        if len(argv) > 1:
            self.openSeries(jser_fp=argv[1])
        else:
            welcome_series = Series(
                os.path.join(
                    welcome_series_dir,
                    "welcome.ser"
                ),
                {0: "welcome.0"}
            )
            welcome_series.src_dir = os.path.dirname(welcome_series_dir)  # set the images directory for the welcome series
            self.openSeries(welcome_series)
        
        self.field.generateView()

        # create menu and shortcuts
        self.createMenuBar()
        self.createContextMenus()
        self.createShortcuts()

        # set the main window as the parent of the progress bar
        setMainWindow(self)

        self.show()

    def createMenuBar(self):
        """Create the menu for the main window."""
        menu = [
            
            {
                "attr_name": "filemenu",
                "text": "File",
                "opts":
                [   
                    ("new_act", "New", "Ctrl+N", self.newSeries),
                    ("open_act", "Open", "Ctrl+O", self.openSeries),
                    None,  # None acts as menu divider
                    ("save_act", "Save", "Ctrl+S", self.saveToJser),
                    ("saveas_act", "Save as...", "", self.saveAsToJser),
                    ("backup_act", "Auto-backup series", "checkbox", self.autoBackup),
                    None,
                    ("fromxml_act", "New from XML series...", "", self.newFromXML),
                    ("exportxml_act", "Export as XML series...", "", self.exportToXML),
                    None,
                    ("username_act", "Change username...", "", self.changeUsername),
                    None,
                    ("restart_act", "Restart", "Ctrl+R", self.restart),
                    None,
                    ("quit_act", "Quit", "Ctrl+Q", self.close),
                ]
            },

            {
                "attr_name": "editmenu",
                "text": "Edit",
                "opts":
                [
                    ("undo_act", "Undo", "Ctrl+Z", self.field.undoState),
                    ("redo_act", "Redo", "Ctrl+Y", self.field.redoState),
                    None,
                    ("cut_act", "Cut", "Ctrl+X", self.field.cut),
                    ("copy_act", "Copy", "Ctrl+C", self.field.copy),
                    ("paste_act", "Paste", "Ctrl+V", self.field.paste),
                    ("pasteattributes_act", "Paste attributes", "Ctrl+B", self.field.pasteAttributes),
                    None,
                    {
                        "attr_name": "bcmenu",
                        "text": "Brightness/contrast",
                        "opts":
                        [
                            ("incbr_act", "Increase brightness", "=", lambda : self.editImage(option="brightness", direction="up")),
                            ("decbr_act", "Decrease brightness", "-", lambda : self.editImage(option="brightness", direction="down")),
                            ("inccon_act", "Increase contrast", "]", lambda : self.editImage(option="contrast", direction="up")),
                            ("deccon_act", "Decrease contrast", "[", lambda : self.editImage(option="contrast", direction="down"))
                        ]
                    }
                ]
            },

            {
                "attr_name": "seriesmenu",
                "text": "Series",
                "opts":
                [
                    {
                        "attr_name": "imagesmenu",
                        "text": "Images",
                        "opts":
                        [
                            ("change_src_act", "Find/change image directory", "", self.changeSrcDir),
                            ("zarrimage_act", "Convert to zarr", "", self.srcToZarr),
                            ("scalezarr_act", "Update zarr scales", "", lambda : self.srcToZarr(create_new=False))
                        ]
                    },
                    None,
                    ("findobjectfirst_act", "Find first object contour...", "Ctrl+F", self.findObjectFirst),
                    None,
                    ("objectlist_act", "Object list", "Ctrl+Shift+O", self.openObjectList),
                    ("ztracelist_act", "Z-trace list", "Ctrl+Shift+Z", self.openZtraceList),
                    ("history_act", "View series history", "", self.viewSeriesHistory),
                    None,
                    {
                        "attr_name": "alignmentsmenu",
                        "text": "Alignments",
                        "opts":
                        [
                            {
                                "attr_name": "importmenu",
                                "text": "Import alignments",
                                "opts":
                                [
                                    ("importtransforms_act", ".txt file", "", self.importTransforms),
                                    ("import_swift_transforms_act", "SWiFT project", "", self.importSwiftTransforms),
                                ]
                            },
                            ("changealignment_act", "Change alignment", "Ctrl+Shift+A", self.changeAlignment),
                            {
                                "attr_name": "propogatemenu",
                                "text": "Propogate transform",
                                "opts":
                                [
                                    ("startpt_act", "Begin propogation", "", lambda : self.field.setPropogationMode(True)),
                                    ("endpt_act", "Finish propogation", "", lambda : self.field.setPropogationMode(False)),
                                    None,
                                    ("proptostart_act", "Propogate to start", "", lambda : self.field.propogateTo(False)),
                                    ("proptoend_act", "Propogate to end", "", lambda : self.field.propogateTo(True))
                                ]
                            }
                        ]
                    },
                    None,
                    {
                        "attr_name": "serieshidemenu",
                        "text": "Hide",
                        "opts":
                        [
                            ("hidealltraces_act", "Hide all traces", "", self.hideSeriesTraces),
                            ("unhidealltraces_act", "Unhide all traces", "", lambda : self.hideSeriesTraces(hidden=False))
                        ]
                    },
                    None,
                    {
                        "attr_name": "importmenu",
                        "text": "Import",
                        "opts":
                        [
                            ("importtraces_act", "Import traces...", "", self.importTraces),
                            ("importzrtraces_act", "Import ztraces...", "", self.importZtraces),
                            ("importtracepalette_act", "Import trace palette...", "", self.importTracePalette),
                            ("importseriestransforms_act", "Import transforms...", "", self.importSeriesTransforms)
                        ]
                    },
                    None,
                    ("smoothing_act", "Modify 3D smoothing...", "", self.edit3DSmoothing),
                    None,
                    ("calibrate_act", "Calibrate pixel size...", "", self.calibrateMag),
                    None,
                    ("resetpalette_act", "Reset trace palette", "", self.resetTracePalette)  
                ]
            },
            
            {
                "attr_name": "sectionmenu",
                "text": "Section",
                "opts":
                [
                    ("nextsection_act", "Next section", "PgUp", self.incrementSection),
                    ("prevsection_act", "Previous section", "PgDown", lambda : self.incrementSection(down=True)),
                    None,
                    ("sectionlist_act", "Section list", "Ctrl+Shift+S", self.openSectionList),
                    ("goto_act", "Go to section", "Ctrl+G", self.changeSection),
                    ("changetform_act", "Change transformation", "Ctrl+T", self.changeTform),
                    None,
                    ("tracelist_act", "Trace list", "Ctrl+Shift+T", self.openTraceList),
                    ("findcontour_act", "Find contour...", "Ctrl+Shift+F", self.field.findContourDialog),
                    None,
                    ("linearalign_act", "Align linear", "", self.field.linearAlign)
                ]
            },

            {
                "attr_name": "viewmenu",
                "text": "View",
                "opts":
                [
                    ("fillopacity_act", "Edit fill opacity...", "", self.setFillOpacity),
                    None,
                    ("homeview_act", "Set view to image", "Home", self.field.home),
                    ("viewmag_act", "View magnification...", "", self.field.setViewMagnification),
                    ("findview_act", "Set zoom for finding contours...", "", self.setFindZoom),
                    None,
                    ("toggleztraces_act", "Toggle show Z-traces", "", self.toggleZtraces),
                    None,
                    ("paletteside_act", "Palette to other side", "Shift+L", self.toggleHandedness),
                    ("cornerbuttons_act",  "Toggle corner buttons", "Shift+T", self.mouse_palette.toggleCornerButtons),
                ]
            },
            {
                "attr_name": "autosegmenu",
                "text": "Autosegment",
                "opts":
                [
                    ("export_zarr_act", "Export to zarr...", "", self.exportToZarr),
                    ("trainzarr_act", "Train...", "", self.train),
                    ("retrainzarr_act", "Retrain...", "", lambda : self.train(retrain=True)),
                    ("predictzarr_act", "Predict (infer)...", "", self.predict),
                    ("sementzarr_act", "Segment...", "", self.segment),
                    {
                        "attr_name": "zarrlayermenu",
                        "text": "Zarr layer",
                        "opts":
                        [
                            ("setzarrlayer_act", "Set zarr layer...", "", self.setZarrLayer),
                            ("removezarrlayer_act", "Remove zarr layer", "", self.removeZarrLayer)
                        ]
                    }
                ]
            }
        ]

        if self.menubar:
            self.menubar.close()

        # Populate menu bar with menus and options
        self.menubar = self.menuBar()
        self.menubar.setNativeMenuBar(False)
        populateMenuBar(self, self.menubar, menu)
    
    def createContextMenus(self):
        """Create the right-click menus used in the field."""
        field_menu_list = [
            ("edittrace_act", "Edit attributes...", "Ctrl+E", self.field.traceDialog),
            {
                "attr_name": "modifymenu",
                "text": "Modify",
                "opts":
                [
                    ("mergetraces_act", "Merge traces", "Ctrl+M", self.field.mergeSelectedTraces),
                    ("mergeobjects_act", "Merge object traces...", "Ctrl+Shift+M", lambda : self.field.mergeSelectedTraces(merge_objects=True)),
                    None,
                    ("makenegative_act", "Make negative", "", self.field.makeNegative),
                    ("makepositive_act", "Make positive", "", lambda : self.field.makeNegative(False)),
                    None,
                    ("markseg_act", "Add to good segmentation group", "Shift+G", self.markKeep)
                ]
            },
            None,
            {
                "attr_name": "viewmenu",
                "text": "View",
                "opts":
                [
                    ("hidetraces_act", "Hide traces", "Ctrl+H", self.field.hideTraces),
                    ("unhideall_act", "Unhide all traces", "Ctrl+U", self.field.unhideAllTraces),
                    None,
                    ("hideall_act", "Toggle hide all", "H", self.field.toggleHideAllTraces),
                    ("showall_act", "Toggle show all", "A", self.field.toggleShowAllTraces),
                    None,
                    ("hideimage_act", "Toggle hide image", "I", self.field.toggleHideImage),
                    ("blend_act", "Toggle section blend", " ", self.field.toggleBlend),
                ]
            },
            None,
            self.cut_act,
            self.copy_act,
            self.paste_act,
            self.pasteattributes_act,
            None,
            ("selectall_act", "Select all traces", "Ctrl+A", self.field.selectAllTraces),
            ("deselect_act", "Deselect traces", "Ctrl+D", self.field.deselectAllTraces),
            None,
            ("deletetraces_act", "Delete traces", "Del", self.field.backspace)
        ]
        self.field_menu = QMenu(self)
        populateMenu(self, self.field_menu, field_menu_list)

        # organize actions
        self.trace_actions = [
            self.edittrace_act,
            self.modifymenu,
            self.mergetraces_act,
            self.makepositive_act,
            self.makenegative_act,
            self.hidetraces_act,
            self.cut_act,
            self.copy_act,
            self.pasteattributes_act,
            self.deletetraces_act
        ]
        self.ztrace_actions = [
            self.edittrace_act
        ]

        # create the label menu
        label_menu_list = [
            ("importlabels_act", "Import label(s)", "", self.importLabels),
            ("mergelabels_act", "Merge labels", "", self.mergeLabels)
        ]
        self.label_menu = QMenu(self)
        populateMenu(self, self.label_menu, label_menu_list)
    
    def checkActions(self, context_menu=False, clicked_trace=None, clicked_label=None):
        """Check for actions that should be enabled or disabled
        
            Params:
                context_menu (bool): True if context menu is being generated
                clicked_trace (Trace): the trace that was clicked on IF the cotext menu is being generated
        """
        # if both traces and ztraces are highlighted or nothing is highlighted, only allow general field options
        if not (bool(self.field.section.selected_traces) ^ 
                bool(self.field.section.selected_ztraces)
        ):
            for a in self.trace_actions:
                a.setEnabled(False)
            for a in self.ztrace_actions:
                a.setEnabled(False)
        # if selected trace in highlighted traces
        elif ((not context_menu and self.field.section.selected_traces) or
              (context_menu and clicked_trace in self.field.section.selected_traces)
        ):
            for a in self.ztrace_actions:
                a.setEnabled(False)
            for a in self.trace_actions:
                a.setEnabled(True)
        # if selected ztrace in highlighted ztraces
        elif ((not context_menu and self.field.section.selected_ztraces) or
              (context_menu and clicked_trace in self.field.section.selected_ztraces)
        ):
            for a in self.trace_actions:
                a.setEnabled(False)
            for a in self.ztrace_actions:
                a.setEnabled(True)
        else:
            for a in self.trace_actions:
                a.setEnabled(False)
            for a in self.ztrace_actions:
                a.setEnabled(False)
            
        # check for objects (to allow merging)
        names = set()
        for trace in self.field.section.selected_traces:
            names.add(trace.name)
        if len(names) > 1:
            self.mergeobjects_act.setEnabled(True)
        else:
            self.mergeobjects_act.setEnabled(False)

        # check labels
        if clicked_label:
            if clicked_label in self.field.zarr_layer.selected_ids:
                self.importlabels_act.setEnabled(True)
                if len(self.zarr_layer.selected_ids) > 1:
                    self.mergelabels_act.setEnabled(True)
            else:
                self.importlabels_act.setEnabled(False)
                self.mergelabels_act.setEnabled(False)
        
        # MENUBAR

        # disable saving for welcome series
        is_not_welcome_series = not self.series.isWelcomeSeries()
        self.save_act.setEnabled(is_not_welcome_series)
        self.saveas_act.setEnabled(is_not_welcome_series)
        self.backup_act.setEnabled(is_not_welcome_series)

        # check for backup directory
        self.backup_act.setChecked(bool(self.series.options["backup_dir"]))

        # undo/redo
        states = self.field.series_states[self.series.current_section]
        has_undo_states = bool(states.undo_states)
        has_redo_states = bool(states.redo_states)
        self.undo_act.setEnabled(has_undo_states)
        self.redo_act.setEnabled(has_redo_states)

        # check clipboard for paste options
        if self.field.clipboard:
            self.paste_act.setEnabled(True)
        else:
            self.paste_act.setEnabled(False)
            self.pasteattributes_act.setEnabled(False)

        # zarr images
        self.zarrimage_act.setEnabled(not self.field.section_layer.is_zarr_file)
        self.scalezarr_act.setEnabled(self.field.section_layer.is_zarr_file)

        # calibrate
        self.calibrate_act.setEnabled(bool(self.field.section.selected_traces))

        # zarr layer
        self.removezarrlayer_act.setEnabled(bool(self.series.zarr_overlay_fp))

    def createShortcuts(self):
        """Create shortcuts that are NOT included in any menus."""
        # domain translate motions
        shortcuts = [
            ("Backspace", self.field.backspace),

            ("/", self.flickerSections),

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
            ("Ctrl+Shift+Right", lambda : self.field.rotateTform(cc=False))
        ]

        for kbd, act in shortcuts:
            QShortcut(QKeySequence(kbd), self).activated.connect(act)
    
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
        
        # mouse mode shortcuts (F1-F8)
        mode_shortcuts = [
            ("p", lambda : self.mouse_palette.activateModeButton("Pointer")),
            ("z", lambda : self.mouse_palette.activateModeButton("Pan/Zoom")),
            ("k", lambda : self.mouse_palette.activateModeButton("Knife")),
            ("c", lambda : self.mouse_palette.activateModeButton("Closed Trace")),
            ("o", lambda : self.mouse_palette.activateModeButton("Open Trace")),
            ("s", lambda : self.mouse_palette.activateModeButton("Stamp"))
        ]
  
        for kbd, act in (mode_shortcuts + trace_shortcuts):
            QShortcut(QKeySequence(kbd), self).activated.connect(act)
    
    def changeSrcDir(self, new_src_dir : str = None, notify=False):
        """Open a series of dialogs to change the image source directory.
        
            Params:
                new_src_dir (str): the new image directory
                notify (bool): True if user is to be notified with a pop-up
        """
        if notify:
            reply = QMessageBox.question(
                self,
                "Images Not Found",
                "Images not found.\nWould you like to locate them?",
                QMessageBox.Yes,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        if new_src_dir is None:
            global fd_dir
            new_src_dir = QFileDialog.getExistingDirectory(
                self,
                "Select folder containing images",
                dir=fd_dir.get()
            )
        if not new_src_dir:
            return
        else:
            if new_src_dir.endswith(".zarr"):
                fd_dir.set(os.path.dirname(new_src_dir))
            else:
                fd_dir.set(new_src_dir)
        self.series.src_dir = new_src_dir
        if self.field:
            self.field.reloadImage()
        self.seriesModified(True)
        
        # prompt user to scale zarr images if not scaled
        if (self.field.section_layer.image_found and 
            self.field.section_layer.is_zarr_file and
            not self.field.section_layer.is_scaled):
            reply = QMessageBox.question(
                self,
                "Zarr Scaling",
                "Zarr file not scaled.\nWould you like to update the zarr with scales?",
                QMessageBox.Yes,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.srcToZarr(create_new=False)
    
    def srcToZarr(self, create_new=True):
        """Convert the series images to zarr."""
        if not self.field.section_layer.image_found:
            notify("Images not found.")
            return
        
        if self.field.section_layer.is_zarr_file and create_new:
            notify("Images are already in zarr format.")
            return
        elif not self.field.section_layer.is_zarr_file and not create_new:
            notify("Images are not in zarr format.\nPlease convert to zarr first.")
            return
        
        if create_new:
            global fd_dir
            zarr_fp, ext = QFileDialog.getSaveFileName(
                self,
                "Convert Images to Zarr",
                os.path.join(fd_dir.get(), f"{self.series.name}_images.zarr"),
                filter="Zarr Directory (*.zarr)"
            )
            if not zarr_fp:
                return
            else:
                fd_dir.set(os.path.dirname(zarr_fp))

        python_bin = sys.executable
        zarr_converter = os.path.join(assets_dir, "scripts", "convert_zarr", "start_process.py")
        if create_new:
            convert_cmd = [python_bin, zarr_converter, self.series.src_dir, zarr_fp]
        else:
            convert_cmd = [python_bin, zarr_converter, self.series.src_dir]

        if os.name == 'nt':

            subprocess.Popen(convert_cmd, creationflags=subprocess.CREATE_NO_WINDOW)
            
        else:

            convert_cmd = " ".join(convert_cmd)
            subprocess.Popen(convert_cmd, shell=True, stdout=None, stderr=None, preexec_fn=os.setpgrp)

    def changeUsername(self, new_name : str = None):
        """Edit the login name used to track history.
        
            Params:
                new_name (str): the new username
        """
        if new_name is None:
            new_name, confirmed = QInputDialog.getText(
                self,
                "Change Login",
                "Enter your desired username:",
                text=os.getlogin()
            )
            if not confirmed or not new_name:
                return
        
        def getlogin():
            return new_name
        
        os.getlogin = getlogin
    
    def setFillOpacity(self, opacity : float = None):
        """Set the opacity of the trace highlight.
        
            Params:
                opacity (float): the new fill opacity
        """
        if opacity is None:
            opacity, confirmed = QInputDialog.getText(
                self,
                "Fill Opacity",
                "Enter fill opacity (0-1):",
                text=str(round(self.series.options["fill_opacity"], 3))
            )
            if not confirmed:
                return
        
        try:
            opacity = float(opacity)
        except ValueError:
            return
        
        if not (0 <= opacity <= 1):
            return
        
        self.series.options["fill_opacity"] = opacity
        self.field.generateView(generate_image=False)

    def openSeries(self, series_obj=None, jser_fp=None):
        """Open an existing series and create the field.
        
            Params:
                series_obj (Series): the series object (optional)
        """
        global fd_dir
        if not series_obj:  # if series is not provided            
            # get the new series
            new_series = None
            if not jser_fp:
                jser_fp, extension = QFileDialog.getOpenFileName(
                    self,
                    "Select Series",
                    dir=fd_dir.get(),
                    filter="*.jser"
                )
                if jser_fp == "": return  # exit function if user does not provide series
                else: fd_dir.set(os.path.dirname(jser_fp))
            
            # user has opened an existing series
            if self.series:
                response = self.saveToJser(notify=True)
                if response == "cancel":
                    return

            # check for a hidden series folder
            sdir = os.path.dirname(jser_fp)
            sname = os.path.basename(jser_fp)
            sname = sname[:sname.rfind(".")]
            hidden_series_dir = os.path.join(sdir, f".{sname}")

            if os.path.isdir(hidden_series_dir):
                # find the series and timer files
                new_series_fp = ""
                sections = {}
                for f in os.listdir(hidden_series_dir):
                    # check if the series is currently being modified
                    if "." not in f:
                        current_time = round(time.time())
                        time_diff = current_time - int(f)
                        if time_diff <= 7:  # the series is currently being operated on
                            QMessageBox.information(
                                self,
                                "Series In Use",
                                "This series is already open in another window.",
                                QMessageBox.Ok
                            )
                            if not self.series:
                                exit()
                            else:
                                return
                    else:
                        ext = f[f.rfind(".")+1:]
                        if ext.isnumeric():
                            sections[int(ext)] = f
                        elif ext == "ser":
                            new_series_fp = os.path.join(hidden_series_dir, f)                    

                # if a series file has been found
                if new_series_fp:
                    # ask the user if they want to open the unsaved series
                    open_unsaved = unsavedNotify()
                    if open_unsaved:
                        new_series = Series(new_series_fp, sections)
                        new_series.modified = True
                        new_series.jser_fp = jser_fp
                    else:
                        # remove the folder if not needed
                        for f in os.listdir(hidden_series_dir):
                            os.remove(os.path.join(hidden_series_dir, f))
                        os.rmdir(hidden_series_dir)
                else:
                    # remove the folder if no series file detected
                    for f in os.listdir(hidden_series_dir):
                        os.remove(os.path.join(hidden_series_dir, f))
                    os.rmdir(hidden_series_dir)

            # open the JSER file if no unsaved series was opened
            if not new_series:
                new_series = Series.openJser(jser_fp)
                # user pressed cancel
                if new_series is None:
                    if self.series is None:
                        exit()
                    else:
                        return
            
            # clear the current series
            if self.series and not self.series.isWelcomeSeries():
                self.series.close()

            self.series = new_series

        # series has already been provided by other function
        else:
            self.series = series_obj
        
        # set the title of the main window
        self.seriesModified(self.series.modified)

        # set the explorer filepath
        if not self.series.isWelcomeSeries():
            fd_dir.set(os.path.dirname(self.series.jser_fp))

        # create field
        if self.field is not None:  # close previous field widget
            self.field.createField(self.series)
        else:
            self.field = FieldWidget(self.series, self)
            self.setCentralWidget(self.field)

        # create mouse palette
        if self.mouse_palette: # close previous mouse dock
            self.mouse_palette.reset(self.series.palette_traces, self.series.current_trace)
        else:
            self.mouse_palette = MousePalette(self.series.palette_traces, self.series.current_trace, self)
            self.createPaletteShortcuts()
        self.changeTracingTrace(self.series.current_trace) # set the current trace

        # ensure that images are found
        if not self.field.section_layer.image_found:
            # check jser directory
            src_path = os.path.join(
                os.path.dirname(self.series.jser_fp),
                os.path.basename(self.field.section.src)
            )
            images_found = os.path.isfile(src_path)
            
            if images_found:
                self.changeSrcDir(src_path)
            else:
                self.changeSrcDir(notify=True)
        # prompt user to scale zarr images if not scaled
        elif (self.field.section_layer.image_found and 
            self.field.section_layer.is_zarr_file and
            not self.field.section_layer.is_scaled):
            reply = QMessageBox.question(
                self,
                "Zarr Scaling",
                "Zarr file not scaled.\nWould you like to update the zarr with scales?",
                QMessageBox.Yes,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.srcToZarr(create_new=False)
    
    def newSeries(
        self,
        image_locations : list = None,
        series_name : str = None,
        mag : float = None,
        thickness : float = None
    ):
        """Create a new series from a set of images.
        
            Params:
                image_locations (list): the filpaths for the section images.
        """
        # get images from user
        if not image_locations:
            global fd_dir
            image_locations, extensions = QFileDialog.getOpenFileNames(
                self,
                "Select Images",
                dir=fd_dir.get(),
                filter="*.jpg *.jpeg *.png *.tif *.tiff *.bmp"
            )
            if len(image_locations) == 0:
                return
            else:
                fd_dir.set(os.path.dirname(image_locations[0]))
        # get the name of the series from user
        if series_name is None:
            series_name, confirmed = QInputDialog.getText(
                self, "New Series", "Enter series name:")
            if not confirmed:
                return
        # get calibration (microns per pix) from user
        if mag is None:
            mag, confirmed = QInputDialog.getDouble(
                self, "New Series", "Enter image calibration (μm/px):",
                0.00254, minValue=0.000001, decimals=6)
            if not confirmed:
                return
        # get section thickness (microns) from user
        if thickness is None:
            thickness, confirmed = QInputDialog.getDouble(
                self, "New Series", "Enter section thickness (μm):",
                0.05, minValue=0.000001, decimals=6)
            if not confirmed:
                return
        
        # save and clear the existing backend series
        self.saveToJser(notify=True, close=True)
        
        # create new series
        series = Series.new(sorted(image_locations), series_name, mag, thickness)
    
        # open series after creating
        self.openSeries(series)

        # prompt the user to save the series
        self.saveAsToJser()
    
    def newFromXML(self, series_fp : str = None):
        """Create a new series from a set of XML files.
        
            Params:
                series_fp (str): the filepath for the XML series
        """

        # get xml series filepath from the user
        if not series_fp:
            global fd_dir
            series_fp, ext = QFileDialog.getOpenFileName(
                self,
                "Select XML Series",
                dir=fd_dir.get(),
                filter="*.ser"
            )
        if series_fp == "": return  # exit function if user does not provide series
        else: fd_dir.set(os.path.dirname(series_fp))

        # save and clear the existing backend series
        self.saveToJser(notify=True, close=True)
        
        # convert the series
        series = xmlToJSON(os.path.dirname(series_fp))
        if not series:
            return

        # open the series
        self.openSeries(series)

        # prompt the user the save the series
        self.saveAsToJser()
    
    def exportToXML(self, export_fp : str = None):
        """Export the current series to XML.
        
            Params:
                export_fp (str): the filepath for the XML .ser file
        """
        # save the current data
        self.saveAllData()

        # get the new xml series filepath from the user
        if not export_fp:
            global fd_dir
            export_fp, ext = QFileDialog.getSaveFileName(
                self,
                "Export Series",
                os.path.join(fd_dir.get(), f"{self.series.name}.ser"),
                filter="XML Series (*.ser)"
            )
            if not export_fp:
                return False
            else:
                fd_dir.set(os.path.dirname(export_fp))
        
        # convert the series
        jsonToXML(self.series, os.path.dirname(export_fp))
    
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
    
    def importTransforms(self, tforms_fp : str = None):
        """Import transforms from a text file.
        
            Params:
                tforms_file (str): the filepath for the transforms file
        """
        self.saveAllData()
        # get file from user
        if tforms_fp is None:
            global fd_dir
            tforms_fp, ext = QFileDialog.getOpenFileName(
                self,
                "Select file containing transforms",
                dir=fd_dir.get()
            )
        if not tforms_fp:
            return
        else:
            fd_dir.set(os.path.dirname(tforms_fp))
        # import the transforms
        importTransforms(self.series, tforms_fp)
        # reload the section
        self.field.reload()

    def importSwiftTransforms(self, tforms_fp : str = None):
        """Import transforms from a text file.
        
            Params:
                tforms_file (str): the filepath for the transforms file
        """
        self.saveAllData()

        swift_fp = None  # Ummmmm, not sure about this?
        
        # get file from user
        if swift_fp is None:
            global fd_dir
            swift_fp, ext = QFileDialog.getOpenFileName(
                self,
                "Select SWiFT project file",
                dir=fd_dir.get()
            )

        if not swift_fp: return
        else: fd_dir.set(os.path.dirname(swift_fp))

        response, confirmed = SwiftDialog(self, swift_fp).exec()
        scale, cal_grid = response

        # import transforms
        print(f'Importing SWiFT transforms at scale {scale}...')
        if cal_grid: print('Cal grid included in series')
        importSwiftTransforms(self.series, swift_fp, scale, cal_grid)
        
        self.field.reload()
    
    def importTraces(self, jser_fp : str = None):
        """Import traces from another jser series.
        
            Params:
                jser_fp (str): the filepath with the series to import data from
        """
        if jser_fp is None:
            global fd_dir
            jser_fp, extension = QFileDialog.getOpenFileName(
                self,
                "Select Series",
                dir=fd_dir.get(),
                filter="*.jser"
            )
        if jser_fp == "": return  # exit function if user does not provide series
        else: fd_dir.set(os.path.dirname(jser_fp))

        self.saveAllData()

        # open the other series
        o_series = Series.openJser(jser_fp)

        # import the traces and close the other series
        self.series.importTraces(o_series)
        o_series.close()

        # reload the field to update the traces
        self.field.reload()

        # refresh the object list if needed
        if self.field.obj_table_manager:
            self.field.obj_table_manager.refresh()
    
    def importZtraces(self, jser_fp : str = None):
        """Import ztraces from another jser series.
        
            Params:
                jser_fp (str): the filepath with the series to import data from
        """
        if jser_fp is None:
            global fd_dir
            jser_fp, extension = QFileDialog.getOpenFileName(
                self,
                "Select Series",
                dir=fd_dir.get(),
                filter="*.jser"
            )
        if jser_fp == "": return  # exit function if user does not provide series
        else: fd_dir.set(os.path.dirname(jser_fp))

        self.saveAllData()

        # open the other series
        o_series = Series.openJser(jser_fp)

        # import the ztraces and close the other series
        self.series.importZtraces(o_series)
        o_series.close()

        # reload the field to update the ztraces
        self.field.reload()

        # refresh the ztrace list if needed
        if self.field.ztrace_table_manager:
            self.field.ztrace_table_manager.refresh()
    
    def importTracePalette(self, jser_fp : str = None):
        """Import the trace palette from another series.
        
            Params:
                jser_fp (str): the filepath with the series to import data from
        """
        if jser_fp is None:
            global fd_dir
            jser_fp, extension = QFileDialog.getOpenFileName(
                self,
                "Select Series",
                dir=fd_dir.get(),
                filter="*.jser"
            )
        if jser_fp == "": return  # exit function if user does not provide series
        else: fd_dir.set(os.path.dirname(jser_fp))

        self.saveAllData()

        # open the other series
        o_series = Series.openJser(jser_fp)

        # import the trace palette
        self.mouse_palette.modifyPalette(o_series.palette_traces)
        self.saveAllData()

        o_series.close()
    
    def importSeriesTransforms(self, jser_fp : str = None):
        """Import the trace palette from another series.
        
            Params:
                jser_fp (str): the filepath with the series to import data from
        """
        if jser_fp is None:
            global fd_dir
            jser_fp, extension = QFileDialog.getOpenFileName(
                self,
                "Select Series",
                dir=fd_dir.get(),
                filter="*.jser"
            )
        if jser_fp == "": return  # exit function if user does not provide series
        else: fd_dir.set(os.path.dirname(jser_fp))

        self.saveAllData()

        # open the other series
        o_series = Series.openJser(jser_fp)

        # preliminary sections check
        self_sections = sorted(list(self.series.sections.keys()))
        other_sections = sorted(list(o_series.sections.keys()))
        if self_sections != other_sections:
            return
        
        # get a list of alignments from the other series
        o_alignments = list(o_series.section_tforms[other_sections[0]].keys())
        s_alignments = list(self.series.section_tforms[other_sections[0]].keys())

        # prompt the user to choose an alignment
        chosen_alignments, confirmed = ImportTransformsDialog(self, o_alignments).exec()
        if not confirmed or not chosen_alignments:
            return
        
        overlap_alignments = []
        for a in chosen_alignments:
            if a in s_alignments:
                overlap_alignments.append(a)
        
        if overlap_alignments:
            overlap_str = ", ".join(overlap_alignments)
            reply = QMessageBox.question(
                self,
                "Import Alignments",
                f"The alignments {overlap_str} exist in your series.\nWould you like to overwrite them?",
                QMessageBox.Yes,
                QMessageBox.No
            )
            if reply == QMessageBox.No:
                notify("Import transforms canceled.")
                return
        
        if chosen_alignments:
            self.series.importTransforms(o_series, chosen_alignments)
        
        self.field.reload()
        self.seriesModified()
    
    def editImage(self, option : str, direction : str):
        """Edit the brightness or contrast of the image.
        
            Params:
                option (str): brightness or contrast
                direction (str): up or down
        """
        if option == "brightness" and direction == "up":
            self.field.changeBrightness(1)
        elif option == "brightness" and direction == "down":
            self.field.changeBrightness(-1)
        elif option == "contrast" and direction == "up":
            self.field.changeContrast(2)
        elif option == "contrast" and direction == "down":
            self.field.changeContrast(-2)
    
    def changeMouseMode(self, new_mode):
        """Change the mouse mode of the field (pointer, panzoom, tracing...).

        Called when user clicks on mouse mode palette.

            Params:
                new_mode: the new mouse mode to set
        """
        self.field.setMouseMode(new_mode)
    
    def changeClosedTraceMode(self, new_mode=None):
        """Change the closed trace mode (trace, rectangle, circle)."""
        if new_mode not in ["trace", "rect", "circle"]:
            new_mode, confirmed = ClosedTraceDialog(self, self.field.closed_trace_mode).exec()
            if not confirmed:
                return
        self.field.closed_trace_mode = new_mode

    def changeTracingTrace(self, trace):
        """Change the trace utilized by the user.

        Called when user clicks on trace palette.

            Params:
                trace: the new tracing trace to set
        """
        self.series.current_trace = trace
        self.field.setTracingTrace(trace)
    
    def changeSection(self, section_num : int = None, save=True):
        """Change the section of the field.
        
            Params:
                section_num (int): the section number to change to
                save (bool): saves data to files if True
        """
        if section_num is None:
            section_num, confirmed = QInputDialog.getText(
                self, "Go To Section", "Enter the desired section number:", text=str(self.series.current_section))
            if not confirmed:
                return
            try:
                section_num = int(section_num)
            except ValueError:
                return
        
        # end the field pending events
        self.field.endPendingEvents()
        # save data
        if save:
            self.saveAllData()
        # change the field section
        self.field.changeSection(section_num)
        # update status bar
        self.field.updateStatusBar()
    
    def flickerSections(self):
        """Switch between the current and b sections."""
        if self.field.b_section:
            self.changeSection(self.field.b_section.n, save=False)
    
    def incrementSection(self, down=False):
        """Increment the section number by one.
        
            Params:
                down (bool): the direction to move
        """
        section_numbers = sorted(list(self.series.sections.keys()))  # get list of all section numbers
        section_number_i = section_numbers.index(self.series.current_section)  # get index of current section number in list
        if down:
            if section_number_i > 0:
                self.changeSection(section_numbers[section_number_i - 1])  
        else:   
            if section_number_i < len(section_numbers) - 1:
                self.changeSection(section_numbers[section_number_i + 1])       
    
    def wheelEvent(self, event):
        """Called when mouse scroll is used."""
        # do nothing if middle button is clicked
        if self.field.mclick:
            return
        
        modifiers = QApplication.keyboardModifiers()

        # if zooming
        if modifiers == Qt.ControlModifier:
            self.activateWindow()
            field_cursor = self.field.cursor()
            p = self.field.mapFromGlobal(field_cursor.pos())
            x, y = p.x(), p.y()
            if not self.is_zooming:
                # check if user just started zooming in
                self.field.panzoomPress(x, y)
                self.zoom_factor = 1
                self.is_zooming = True

            if event.angleDelta().y() > 0:  # if scroll up
                self.zoom_factor *= 1.1
            elif event.angleDelta().y() < 0:  # if scroll down
                self.zoom_factor *= 0.9
            self.field.panzoomMove(zoom_factor=self.zoom_factor)
        
        # if changing sections
        elif modifiers == Qt.NoModifier:
            # check for the position of the mouse
            mouse_pos = event.point(0).pos()
            field_geom = self.field.geometry()
            if not field_geom.contains(mouse_pos.x(), mouse_pos.y()):
                return
            # change the section
            if event.angleDelta().y() > 0:  # if scroll up
                self.incrementSection()
            elif event.angleDelta().y() < 0:  # if scroll down
                self.incrementSection(down=True)
    
    def keyReleaseEvent(self, event):
        """Overwritten: checks for Ctrl+Zoom."""
        if self.is_zooming and event.key() == 16777249:
            self.field.panzoomRelease(zoom_factor=self.zoom_factor)
            self.is_zooming = False
        
        super().keyReleaseEvent(event)
    
    def saveAllData(self):
        """Write current series and section data into backend JSON files."""
        if self.series.isWelcomeSeries():
            return
        # save the trace palette
        self.series.palette_traces = []
        for button in self.mouse_palette.palette_buttons:  # get trace palette
            self.series.palette_traces.append(button.trace)
            if button.isChecked():
                self.series.current_trace = button.trace
        self.field.section.save()
        self.series.save()
    
    def saveToJser(self, notify=False, close=False):
        """Save all data to JSER file.
        
        Params:
            save_data (bool): True if series and section files in backend should be save
            close (bool): Deletes backend series if True
        """
        # save the series data
        self.saveAllData()

        # if welcome series -> close without saving
        if self.series.isWelcomeSeries():
            return
        
        # notify the user and check if series was modified
        if notify and self.series.modified:
            save = saveNotify()
            if save == "no":
                if close:
                    self.series.close()
                return
            elif save == "cancel":
                return "cancel"
        
        # check if the user is closing and the series was not modified
        if close and not self.series.modified:
            self.series.close()
            return

        # run save as if there is no jser filepath
        if not self.series.jser_fp:
            self.saveAsToJser(close=close)
        else:        
            self.series.saveJser(close=close)
        
        # set the series to unmodified
        self.seriesModified(False)
    
    def saveAsToJser(self, close=False):
        """Prompt the user to find a save location."""
        # save the series data
        self.saveAllData()

        # check for wlecome series
        if self.series.isWelcomeSeries():
            return

        # get location from user
        new_jser_fp, confirmed = getSaveLocation(self.series)
        if not confirmed:
            return
        
        # move the working hidden folder to the new jser directory
        self.series.move(
            new_jser_fp,
            self.field.section,
            self.field.b_section
        )
        
        # save the file
        self.series.saveJser(close=close)

        # set the series to unmodified
        self.seriesModified(False)
    
    def autoBackup(self):
        """Set up the auto-backup functionality for the series."""
        # user checked the option
        if self.backup_act.isChecked():
            # prompt the user to find a folder to store backups
            global fd_dir
            new_dir = QFileDialog.getExistingDirectory(
                self,
                "Select folder to contain backup files",
                dir=fd_dir.get()
            )
            if not new_dir:
                self.backup_act.setChecked(False)
                return
            else:
                fd_dir.set(new_dir)
            self.series.options["backup_dir"] = new_dir
        # user unchecked the option
        else:
            self.series.options["backup_dir"] = ""
        
        self.seriesModified()
    
    def viewSeriesHistory(self):
        """View the history for the entire series."""
        # load all log objects from the all traces
        log_history = []
        update, canceled = progbar("Object History", "Loading history...")
        progress = 0
        final_value = len(self.series.sections)
        for snum in self.series.sections:
            section = self.series.loadSection(snum)
            for trace in section.tracesAsList():
                for log in trace.history:
                    log_history.append((log, trace.name, snum))
            if canceled():
                return
            progress += 1
            update(progress/final_value * 100)
        
        log_history.sort()

        output_str = "Series History\n"
        for log, name, snum in log_history:
            output_str += f"Section {snum} "
            output_str += name + " "
            output_str += str(log) + "\n"
        
        self.history_widget = HistoryWidget(self, output_str)
    
    def openObjectList(self):
        """Open the object list widget."""
        self.saveAllData()
        self.field.openObjectList()
    
    def openZtraceList(self):
        """Open the ztrace list widget."""
        self.saveAllData()
        self.field.openZtraceList()
    
    def toggleZtraces(self):
        """Toggle whether ztraces are shown."""
        self.field.deselectAllTraces()
        self.series.options["show_ztraces"] = not self.series.options["show_ztraces"]
        self.field.generateView(generate_image=False)
    
    def openTraceList(self):
        """Open the trace list widget."""
        self.field.openTraceList()
    
    def openSectionList(self):
        """Open the section list widget."""
        self.saveAllData()
        self.field.openSectionList()
    
    def setToObject(self, obj_name : str, section_num : str):
        """Focus the field on an object from a specified section.
        
            Params:
                obj_name (str): the name of the object
                section_num (str): the section the object is located
        """
        self.changeSection(section_num)
        self.field.findContour(obj_name)
    
    def findObjectFirst(self, obj_name=None):
        """Find the first or last contour in the series.
        
            Params:
                obj_name (str): the name of the object to find
        """
        if obj_name is None:
            obj_name, confirmed = QInputDialog.getText(
                self,
                "Find Object",
                "Enter the object name:",
            )
            if not confirmed:
                return

        # find the contour
        if self.field.obj_table_manager:
            self.field.obj_table_manager.findObject(obj_name, first=True)
        else:
            for snum, section in self.series.enumerateSections(
                show_progress=False):
                if obj_name in section.contours:
                    self.setToObject(obj_name, snum)
                    return
    
    def changeTform(self, new_tform_list : list = None):
        """Open a dialog to change the transform of a section."""
        # check for section locked status
        if self.field.section.align_locked:
            return
        
        if new_tform_list is None:
            current_tform = " ".join(
                [str(round(n, 5)) for n in self.field.section.tforms[self.series.alignment].getList()]
            )
            new_tform_list, confirmed = QInputDialog.getText(
                self, "New Transform", "Enter the desired section transform:", text=current_tform)
            if not confirmed:
                return
            try:
                new_tform_list = [float(n) for n in new_tform_list.split()]
                if len(new_tform_list) != 6:
                    return
            except ValueError:
                return
        self.field.changeTform(Transform(new_tform_list))
    
    def translate(self, direction : str, amount : str):
        """Translate the current transform.
        
            Params:
                direction (str): left, right, up, or down
                amount (str): small, med, or big
        """
        if amount == "small":
            num = self.series.options["small_dist"]
        elif amount == "med":
            num = self.series.options["med_dist"]
        elif amount == "big":
            num = self.series.options["big_dist"]
        if direction == "left":
            x, y = -num, 0
        elif direction == "right":
            x, y = num, 0
        elif direction == "up":
            x, y = 0, num
        elif direction == "down":
            x, y = 0, -num
        self.field.translate(x, y)
    
    def newAlignment(self, new_alignment_name : str):
        """Add a new alignment (based on existing alignment).
        
            Params:
                new_alignment_name (str): the name of the new alignment
        """
        if new_alignment_name in self.field.section.tforms:
            QMessageBox.information(
                self,
                " ",
                "This alignment already exists.",
                QMessageBox.Ok
            )
            return
        self.series.newAlignment(
            new_alignment_name,
            self.series.alignment
        )
    
    def changeAlignment(self, alignment_name : str = None):
        """Open dialog to modify and change alignments.
        
            Params:
                alignment_name (str): the name of the alignment ro switch to
        """
        alignments = list(self.field.section.tforms.keys())

        if alignment_name is None:
            response, confirmed = AlignmentDialog(
                self,
                alignments
            ).exec()
            if not confirmed:
                return
            (
                alignment_name,
                added,
                removed,
                renamed
            ) = response
        else:
            added, removed, renamed = [], [], []
        
        if added or removed or renamed:
            self.series.modifyAlignments(added, removed, renamed)
            self.field.reload()
        
        if alignment_name:
            self.field.changeAlignment(alignment_name)
    
    def calibrateMag(self, trace_lengths : dict = None):
        """Calibrate the pixel size for the series.
        
            Params:
                trace_lengths (dict): the lengths of traces to calibrate
        """
        self.saveAllData()
        
        if trace_lengths is None:
            # gather trace names
            names = []
            for trace in self.field.section.selected_traces:
                if trace.name not in names:
                    names.append(trace.name)
            
            if len(names) == 0:
                notify("Please select traces for calibration.")
            
            # prompt user for length of each trace name
            trace_lengths = {}
            for name in names:
                d, confirmed = QInputDialog.getText(
                    self,
                    "Trace Length",
                    f'Length of "{name}" in microns:'
                )
                if not confirmed:
                    return
                try:
                    d = float(d)
                except ValueError:
                    return
                trace_lengths[name] = d
        
        self.field.calibrateMag(trace_lengths)
    
    def modifyPointer(self, event=None):
        """Modify the pointer properties."""
        response, confirmed = PointerDialog(
            self,
            tuple(self.series.options["pointer"])
        ).exec()
        if not confirmed:
            return
        self.series.options["pointer"] = response
        self.seriesModified()
    
    def modifyGrid(self, event=None):
        """Modify the grid properties."""
        response, confirmed = GridDialog(
            self,
            tuple(self.series.options["grid"])
        ).exec()
        if not confirmed:
            return
        
        self.series.options["grid"] = response
        self.seriesModified()
    
    def toggleHandedness(self):
        """Toggle the handedness of the palettes."""
        self.mouse_palette.toggleHandedness()
        if self.zarr_palette:
            self.zarr_palette.toggleHandedness()
    
    def resetTracePalette(self):
        """Reset the trace palette to default traces."""
        self.mouse_palette.resetPalette()
        self.saveAllData()
        self.seriesModified()
    
    def setZarrLayer(self, zarr_dir=None):
        """Set a zarr layer."""
        if not zarr_dir:
            global fd_dir
            zarr_dir = QFileDialog.getExistingDirectory(
                self,
                "Select overlay zarr",
                dir=fd_dir.get()
            )
            if not zarr_dir:
                return
            else:
                fd_dir.set(os.path.dirname(zarr_dir))

        self.series.zarr_overlay_fp = zarr_dir
        self.series.zarr_overlay_group = None

        groups = []
        for g in os.listdir(zarr_dir):
            if os.path.isdir(os.path.join(zarr_dir, g)):
                groups.append(g)

        self.zarr_palette = ZarrPalette(groups, self)
    
    def setLayerGroup(self, group_name):
        """Set the specific group displayed in the zarr layer."""
        if not group_name:
            group_name = None
        if self.zarr_palette.cb.currentText != group_name:
            self.zarr_palette.cb.setCurrentText(group_name)
        self.series.zarr_overlay_group = group_name
        self.field.createZarrLayer()
        self.field.generateView()
    
    def removeZarrLayer(self):
        """Remove an existing zarr layer."""
        self.series.zarr_overlay_fp = None
        self.series.zarr_overlay_group = None
        if self.zarr_palette:
            self.zarr_palette.close()
        self.field.createZarrLayer()
        self.field.generateView()

    def exportToZarr(self):
        """Set up an autosegmentation for a series.
        
            Params:
                run (str): "train" or "segment"
        """
        self.saveAllData()
        self.removeZarrLayer()

        if not self.series.jser_fp:
            self.saveAsToJser()
            if not self.series.jser_fp:
                return

        inputs, dialog_confirmed = CreateZarrDialog(self, self.series).exec()

        if not dialog_confirmed: return

        print("Making zarr directory...")
        
        # export to zarr
        border_obj, srange, mag = inputs
        data_fp = seriesToZarr(
            self.series,
            border_obj,
            srange,
            mag
        )

        self.series.options["autoseg"]["zarr_current"] = data_fp

        print("Zarr directory done.")
    
    def train(self, retrain=False):
        """Train an autosegmentation model."""
        self.saveAllData()
        self.removeZarrLayer()

        print("Importing training modules...")

        from autoseg import train, make_mask, model_paths
        # model_paths = {"a":{"b":"a/b/m.py"}}

        opts = self.series.options["autoseg"]

        response, confirmed = TrainDialog(self, self.series, model_paths, opts, retrain).exec()
        if not confirmed: return
        
        (data_fp, iterations, save_every, group, model_path, cdir, \
         pre_cache, min_masked, downsample) = response

        training_opts = {
            'zarr_current': data_fp,
            'iters': iterations,
            'save_every': save_every,
            'group': group,
            'model_path': model_path,
            'checkpts_dir': cdir,
            'pre_cache': pre_cache,
            'min_masked': min_masked,
            'downsample_bool': downsample
        }

        for k, v in training_opts.items():
            opts[k] = v
        self.seriesModified(True)

        print("Exporting labels to zarr directory...")
        
        if retrain:
            group_name = f"labels_{self.series.getRecentSegGroup()}_keep"
            seriesToLabels(self.series, data_fp)
            
        else:
            group_name = f"labels_{group}"
            seriesToLabels(self.series, data_fp, group)

        print("Zarr directory updated with labels!")

        if retrain: self.field.reload()
        if retrain and self.field.obj_table_manager:
            self.field.obj_table_manager.refresh()

        print("Starting training....")

        make_mask(data_fp, group_name)
        
        sources = [{
            "raw" : (data_fp, "raw"),
            "labels" : (data_fp, group_name),
            "unlabelled" : (data_fp, "unlabelled")
        }]

        train(
            iterations=iterations,
            save_every=save_every,
            sources=sources,
            model_path=model_path,
            pre_cache=pre_cache,
            min_masked=min_masked,
            downsample=downsample,
            checkpoint_basename=os.path.join(cdir, "model")  # where existing checkpoints
        )

        print("Done training!")
    
    def markKeep(self):
        """Add the selected trace to the most recent "keep" segmentation group."""
        keep_tag = f"{self.series.getRecentSegGroup()}_keep"
        for trace in self.field.section.selected_traces:
            trace.addTag(keep_tag)
        # deselect traces and hide
        self.field.hideTraces()
        self.field.deselectAllTraces()

    def predict(self, data_fp : str = None):
        """Run predictons.
        
            Params:
                data_fp (str): the filepath for the zarr
        """
        self.saveAllData()
        self.removeZarrLayer()

        print("Importing models...")
        
        from autoseg import predict, model_paths
        # model_paths = {"a":{"b":"a/b/m.py"}}

        opts = self.series.options["autoseg"]

        response, dialog_confirmed = PredictDialog(self, model_paths, opts).exec()

        if not dialog_confirmed: return

        data_fp, model_path, cp_path, write_opts, increase, downsample, full_out_roi = response

        predict_opts = {
            'zarr_current': data_fp,
            'model_path': model_path,
            'checkpts_dir': os.path.dirname(cp_path),
            'write': write_opts,
            'increase': increase,
            'downsample_bool': downsample,
            'full_out_roi': full_out_roi
        }

        for k, v in predict_opts.items():
            opts[k] = v
        self.seriesModified(True)
                
        print("Running predictions...")

        zarr_datasets = predict(
            sources=[(data_fp, "raw")],
            out_file=data_fp,
            checkpoint_path=cp_path,
            model_path=model_path,
            write=write_opts,
            increase=increase,
            downsample=downsample,
            full_out_roi=full_out_roi
        )

        # display the affinities
        self.setZarrLayer(data_fp)
        for zg in os.listdir(data_fp):
            if zg.startswith("pred_affs"):
                self.setLayerGroup(zg)
                break

        print("Predictions done.")
        
    def segment(self, data_fp : str = None):
        """Run an autosegmentation.
        
            Params:
                data_fp (str): the filepath for the zarr
        """
        self.saveAllData()
        self.removeZarrLayer()

        print("Importing modules...")
        
        from autoseg import hierarchical

        opts = self.series.options["autoseg"]

        response, dialog_confirmed = SegmentDialog(self, opts).exec()

        if not dialog_confirmed: return

        data_fp, thresholds, downsample, norm_preds, min_seed, merge_fun = response

        segment_opts = {
            "zarr_current": data_fp,
            "thresholds": thresholds,
            "downsample_int": downsample,
            "norm_preds": norm_preds,
            "min_seed": min_seed,
            "merge_fun": merge_fun
        }

        for k, v in segment_opts.items():
            opts[k] = v
        self.seriesModified(True)

        print("Running hierarchical...")

        dataset = None
        for d in os.listdir(data_fp):
            if "affs" in d:
                dataset = d
                break

        print("Segmentation started...")
            
        hierarchical.run(
            data_fp,
            dataset,
            thresholds=list(sorted(thresholds)),
            normalize_preds=norm_preds,
            min_seed_distance=min_seed,
            merge_function=merge_fun
        )

        print("Segmentation done.")

        # display the segmetnation
        self.setZarrLayer(data_fp)
        for zg in os.listdir(data_fp):
            if zg.startswith("seg"):
                self.setLayerGroup(zg)
                break
    
    def importLabels(self, all=False):
        """Import labels from a zarr."""
        if not self.field.zarr_layer or not self.field.zarr_layer.is_labels:
            return
        
        # get necessary data
        data_fp = self.series.zarr_overlay_fp
        group_name = self.series.zarr_overlay_group

        labels = None if all else self.field.zarr_layer.selected_ids
        
        labelsToObjects(
            self.series,
            data_fp,
            group_name,
            labels
        )
        self.field.reload()
        self.removeZarrLayer()

        if self.field.obj_table_manager:
            self.field.obj_table_manager.refresh()
    
    def mergeLabels(self):
        """Merge selected labels in a zarr."""
        if not self.field.zarr_layer:
            return
        
        self.field.zarr_layer.mergeLabels()
        self.field.generateView()
    
    def mergeObjects(self, new_name=None):
        """Merge full objects across the series.
        
            Params:
                new_name (str): the new name for the merged objects
        """            
        names = set()
        for trace in self.field.section.selected_traces:
            names.add(trace.name)
        names = list(names)
        
        if not new_name:
            new_name, confirmed = QInputDialog.getText(
                self,
                "Object Name",
                "Enter the desired name for the merged object:",
                text=names[0]
            )
            if not confirmed or not new_name:
                return
        
        self.series.mergeObjects(names, new_name)
        self.field.reload()
    
    def edit3DSmoothing(self, smoothing_alg : str = ""):
        """Modify the algorithm used for 3D smoothing.
        
            Params:
                smoothing_alg (str): the name of the smoothing algorithm to use
        """
        if not smoothing_alg:
            smoothing_alg, confirmed = SmoothingDialog(self, self.series.options["3D_smoothing"]).exec()
            if not confirmed:
                return
        
        if smoothing_alg not in ["laplacian", "humphrey", "none"]:
            return

        self.series.options["3D_smoothing"] = smoothing_alg
        self.saveAllData()
        self.seriesModified()
    
    def hideSeriesTraces(self, hidden=True):
        """Hide or unhide all traces in the entire series.
        
            Params:
                hidden (bool) True if traces will be hidden
        """
        self.saveAllData()
        self.series.hideAllTraces(hidden)
        self.field.reload()
    
    def setFindZoom(self):
        """Set the magnification for find contour."""
        z, confirmed = QInputDialog.getInt(
            self,
            "Find Contour Zoom",
            "Enter the find contour zoom (0-100):",
            value=self.series.options["find_zoom"],
            minValue=0,
            maxValue=100
        )
        if not confirmed:
            return

        self.series.options["find_zoom"] = z

    def restart(self):
        self.restart_mainwindow = True

        # Clear console
        
        if os.name == 'nt':  # Windows
            _ = os.system('cls')
        
        else:  # Mac and Linux
            _ = os.system('clear')
        
        self.close()
            
    def closeEvent(self, event):
        """Save all data to files when the user exits."""
        if self.series.options["autosave"]:
            self.saveToJser(close=True)
        else:
            response = self.saveToJser(notify=True, close=True)
            if response == "cancel":
                event.ignore()
                return
        event.accept()
