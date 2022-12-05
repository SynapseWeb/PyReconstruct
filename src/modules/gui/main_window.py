import os
from time import time

from PySide6.QtWidgets import (
    QMainWindow, 
    QFileDialog,
    QInputDialog, 
    QApplication,
    QMessageBox, 
    QMenu
)
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import Qt

from modules.gui.mouse_palette import MousePalette
from modules.gui.field_widget import FieldWidget
from modules.gui.dialog import AlignmentDialog
from modules.gui.history_widget import HistoryWidget

from modules.gui.gui_functions import progbar
from modules.backend.xml_json_conversions import xmlToJSON, jsonToXML
from modules.backend.import_transforms import importTransforms
from modules.gui.gui_functions import populateMenuBar, populateMenu

from modules.pyrecon.series import Series
from modules.pyrecon.transform import Transform

from constants.locations import assets_dir


class MainWindow(QMainWindow):

    def __init__(self):
        """Constructs the skeleton for an empty main window."""
        super().__init__() # initialize QMainWindow
        self.setWindowTitle("pyReconstruct")

        # set the main window to be slightly less than the size of the monitor
        screen = QApplication.primaryScreen()
        screen_rect = screen.size()
        x = 50
        y = 80
        w = screen_rect.width() - 100
        h = screen_rect.height() - 160
        self.setGeometry(x, y, w, h)

        # misc defaults
        self.field = None  # placeholder for field
        self.mouse_palette = None  # placeholder for mouse palette
        self.setMouseTracking(True) # set constant mouse tracking for various mouse modes
        self.is_zooming_in = False
        # number defaults
        self.smallnum = 0.01
        self.mednum = 0.1
        self.bignum = 1

        # create status bar at bottom of window
        self.statusbar = self.statusBar()

        # open series and create field
        welcome_series = Series(os.path.join(assets_dir, "welcome_series", "welcome.ser"))
        self.openSeries(welcome_series, refresh_menu=False)
        self.field.generateView()

        # create menu and shortcuts
        self.createMenuBar()
        self.createContextMenus()
        self.createShortcuts()

        self.show()

    def createMenuBar(self):
        """Create the menu for the main window."""
        if self.series.filetype == "XML":
            outtype = "json"
        elif self.series.filetype == "JSON":
            outtype = "xml"

        menu = [
            
            {
                "attr_name": "filemenu",
                "text": "File",
                "opts":
                [   
                    ("new_act", "New", "Ctrl+N", self.newSeries),
                    ("open_act", "Open", "Ctrl+O", self.openSeries),
                    None,  # None acts as menu divider
                    ("save_act", "Save", "Ctrl+S", self.saveAllData),
                    ("close_act", "Close", "Ctrl+Q", self.close),
                    None,
                    ("export_series_act", f"Export to {outtype}", "", self.exportSeries),
                    ("import_transforms_act", "Import transformations", "", self.importTransforms),
                    None,
                    ("username_act", "Change username...", "", self.changeUsername)
                ]
            },

            {
                "attr_name": "editmenu",
                "text": "Edit",
                "opts":
                [
                    ("undo_act", "Undo", "Ctrl+Z", self.field.undoState),
                    ("red_act", "Redo", "Ctrl+Y", self.field.redoState),
                    None,
                    ("cut_act", "Cut", "Ctrl+X", self.field.cut),
                    ("copy_act", "Copy", "Ctrl+C", self.field.copy),
                    ("paste_act", "Paste", "Ctrl+V", self.field.paste),
                    ("pasteattributes_act", "Paste attributes", "Ctrl+B", self.field.pasteAttributes),
                    None,
                    ("incbr_act", "Increase brightness", "=", lambda : self.editImage(option="brightness", direction="up")),
                    ("decbr_act", "Decrease brightness", "-", lambda : self.editImage(option="brightness", direction="down")),
                    ("inccon_act", "Increase contrast", "]", lambda : self.editImage(option="contrast", direction="up")),
                    ("deccon_act", "Decrease contrast", "[", lambda : self.editImage(option="contrast", direction="down"))
                ]
            },

            {
                "attr_name": "seriesmenu",
                "text": "Series",
                "opts":
                [
                    ("change_src_act", "Find images", "", self.changeSrcDir),
                    None,
                    ("objectlist_act", "Object list", "Ctrl+Shift+O", self.openObjectList),
                    ("ztracelist_act", "Z-trace list", "", self.openZtraceList),
                    ("history_act", "View series history", "", self.viewSeriesHistory),
                    None,
                    ("changealignment_act", "Change alignment", "Ctrl+Shift+A", self.changeAlignment)                 
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
                    ("findcontour_act", "Find contour...", "Ctrl+F", self.field.findContourDialog),
                    ("tracelist_act", "Open trace list", "Ctrl+Shift+T", self.openTraceList),
                    None,
                    ("sectionlist_act", "Open section list", "Ctrl+Shift+S", self.openSectionList),
                    ("goto_act", "Go to section", "Ctrl+G", self.gotoSection),
                    ("changetform_act", "Change transformation", "Ctrl+T", self.changeTform),
                ]
            },

            {
                "attr_name": "viewmenu",
                "text": "View",
                "opts":
                [
                    ("highlightopacity_act", "Edit fill opacity...", "", self.setFillOpacity),
                    None,
                    ("homeview_act", "Set view to image", "Home", self.field.home),
                    ("viewmag_act", "View magnification...", "", self.field.setViewMagnification),
                    None,
                    ("paletteside_act", "Toggle palette side", "Shift+L", self.mouse_palette.toggleHandedness),
                    ("cornerbuttons_act",  "Toggle corner buttons", "Shift+T", self.mouse_palette.toggleCornerButtons)
                ]
            }
        ]

        # Populate menu bar with menus and options
        self.menubar = self.menuBar()
        populateMenuBar(self, self.menubar, menu)
    
    def createContextMenus(self):
        """Create the right-click menus used in the field."""
        field_menu_list = [
            ("deselect_act", "Deselect traces", "Ctrl+D", self.field.deselectAllTraces),
            ("selectall_act", "Select all traces", "Ctrl+A", self.field.selectAllTraces),
            ("hideall_act", "Toggle visibility of all traces", "H", self.field.toggleHideAllTraces),
            ("unhideall_act", "Unhide all traces", "Ctrl+U", self.field.unhideAllTraces),
            ("blend_act", "Toggle section blend", " ", self.field.toggleBlend),
        ]
        self.field_menu = QMenu(self)
        populateMenu(self, self.field_menu, field_menu_list)

        trace_menu_list = [
            ("edittrace_act", "Edit trace attributes...", "Ctrl+E", self.field.traceDialog),
            ("mergetraces_act", "Merge traces", "Ctrl+M", self.field.mergeSelectedTraces),
            ("hidetraces_act", "Hide traces", "Ctrl+H", self.field.hideTraces),
            ("deletetraces_act", "Delete traces", "Del", self.field.deleteTraces),
            {
                "attr_name": "negativemenu",
                "text": "Negative",
                "opts":
                [
                    ("makenegative_act", "Make negative", "", self.field.makeNegative),
                    ("makepositive_act", "Make positive", "", lambda : self.field.makeNegative(False))
                ]
            },
            None,
            self.cut_act,
            self.copy_act,
            self.paste_act,
            self.pasteattributes_act,
            None,
            self.deselect_act,
            self.selectall_act,
            self.hideall_act,
            self.blend_act
        ]
        self.trace_menu = QMenu(self)
        populateMenu(self, self.trace_menu, trace_menu_list)

    def createShortcuts(self):
        """Create shortcuts that are NOT included in any menus."""
        # domain translate motions
        shortcuts = [
            ("Backspace", self.field.backspace),

            ("/", self.field.flickerSections),

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
            ("Shift+Down", lambda : self.translate("down", "big"))
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
    
    def changeSrcDir(self, notify=False):
        """Open a series of dialogs to change the image source directory.
        
            Params:
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
        new_src_dir = QFileDialog.getExistingDirectory(self, "Select folder containing images")
        if not new_src_dir:
            return
        if os.path.samefile(new_src_dir, self.series.getwdir()):
            self.series.src_dir = ""
        else:
            self.series.src_dir = new_src_dir
        QMessageBox.information(
            self,
            "Image Directory",
            "New image directory saved.",
            QMessageBox.Ok
        )
        self.field.reloadImage()
    
    def changeUsername(self):
        """Edit the login name used to track history."""
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
    
    def setFillOpacity(self):
        """Set the opacity of the trace highlight."""
        opacity, confirmed = QInputDialog.getText(
            self,
            "Fill Opacity",
            "Enter fill opacity (0-1):",
            text=str(round(self.series.fill_opacity, 3))
        )
        if not confirmed:
            return
        
        try:
            opacity = float(opacity)
        except ValueError:
            return
        
        if not (0 <= opacity <= 1):
            return
        
        self.series.fill_opacity = opacity
        self.field.generateView(generate_image=False)

    def openSeries(self, series_obj=None, refresh_menu=True):
        """Open an existing series and create the field.
        
            Params:
                series_obj (Series): the series object (optional)
                refresh_menu (bool): True if menu is remade
        """
        if not series_obj:  # if series is not provided
            series_fp, extension = QFileDialog.getOpenFileName(self, "Select Series", filter="*.ser")
            if series_fp == "": return  # exit function if user does not provide series
            self.series = Series(series_fp)  # load series data into Series object
        else:
            self.series = series_obj
        
        # ensure that images are found
        section = self.series.loadSection(self.series.current_section)
        if self.series.src_dir == "":
            src_path = os.path.join(self.series.getwdir(), os.path.basename(section.src))
        else:
            src_path = os.path.join(self.series.src_dir, os.path.basename(section.src))
        if not (os.path.isfile(src_path) or os.path.isdir(src_path)):
            self.changeSrcDir(notify=True)

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

        # refresh export choice on menu
        if refresh_menu:
            if self.series.filetype == "XML":
                outtype = "JSON"
            elif self.series.filetype == "JSON":
                outtype = "XML"
            self.export_series_act.setText(f"Export series to {outtype}...")
    
    def newSeries(self, image_locations : list = None):
        """Create a new series from a set of images.
        
            Params:
                image_locations (list): the filpaths for the section images.
        """
        # get images from user
        if not image_locations:
            image_locations, extensions = QFileDialog.getOpenFileNames(
                self, "Select Images", filter="*.jpg *.jpeg *.png *.tif *.tiff")
            if len(image_locations) == 0:
                return
        # get the name of the series from user
        series_name, confirmed = QInputDialog.getText(
            self, "New Series", "Enter series name:")
        if not confirmed:
            return
        # get calibration (microns per pix) from user
        mag, confirmed = QInputDialog.getDouble(
            self, "New Series", "Enter image calibration (μm/px):",
            0.00254, minValue=0.000001, decimals=6)
        if not confirmed:
            return
        # get section thickness (microns) from user
        thickness, confirmed = QInputDialog.getDouble(
            self, "New Series", "Enter section thickness (μm):",
            0.05, minValue=0.000001, decimals=6)
        if not confirmed:
            return
        # store directory to folder with images
        first_image = image_locations[0]
        if "/" in first_image:
            self.wdir = first_image[:first_image.rfind("/")+1]
        
        # create new series
        series = Series.new(image_locations, series_name, mag, thickness)
    
        # open series after creating
        self.openSeries(series)
    
    def exportSeries(self):
        """Export the series to a given filetype."""
        new_dir = QFileDialog.getExistingDirectory(self, "Find Destination Folder to Contain Series")
        if not new_dir:
            return
        if self.series.filetype == "XML":
            xmlToJSON(self.series, new_dir)
        elif self.series.filetype == "JSON":
            jsonToXML(self.series, new_dir)
    
    def importTransforms(self):
        """Import transforms from a text file."""
        self.saveAllData()
        # get file from user
        tforms_file, ext = QFileDialog.getOpenFileName(self, "Select file containing transforms")
        if not tforms_file:
            return
        # import the transforms
        importTransforms(self.series, tforms_file)
        # reload the section
        self.field.reload()
    
    def editImage(self, option : str, direction : str):
        """Edit the brightness or contrast of the image.
        
            Params:
                option (str): brightness or contrast
                direction (str): up or down
        """
        if option == "brightness" and direction == "up":
            self.field.changeBrightness(5)
        elif option == "brightness" and direction == "down":
            self.field.changeBrightness(-5)
        elif option == "contrast" and direction == "up":
            self.field.changeContrast(0.2)
        elif option == "contrast" and direction == "down":
            self.field.changeContrast(-0.2)
    
    def changeMouseMode(self, new_mode):
        """Change the mouse mode of the field (pointer, panzoom, tracing...).

        Called when user clicks on mouse mode palette.

            Params:
                new_mode: the new mouse mode to set
        """
        self.field.setMouseMode(new_mode)

    def changeTracingTrace(self, trace):
        """Change the trace utilized by the user.

        Called when user clicks on trace palette.

            Params:
                trace: the new tracing trace to set
        """
        self.series.current_trace = trace
        self.field.setTracingTrace(trace)
    
    def changeSection(self, section_num : int, save=True):
        """Change the section of the field.
        
            Params:
                section_num (int): the section number to change to
                save (bool): saves data to files if True
        """
        start_time = time()
        # save data
        if save:
            self.saveAllData()
        # change the field section
        self.field.changeSection(section_num)
        # update status bar
        self.field.updateStatusBar()
        print(f"Time taken to change to section {section_num}:", time() - start_time, "sec")
    
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
            if not self.is_zooming_in:
                # check if user just started zooming in
                self.field.panzoomPress(
                    event.point(0).pos().x() - self.field.x(),
                    event.point(0).pos().y() - self.field.y(),
                )
                self.zoom_factor = 1
                self.is_zooming_in = True

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
        if self.is_zooming_in and event.key() == 16777249:
            self.field.panzoomRelease(zoom_factor=self.zoom_factor)
            self.is_zooming_in = False
        
        super().keyReleaseEvent(event)
    
    def saveAllData(self):
        """Write current series and section data into JSON files."""
        # save the trace palette
        self.series.palette_traces = []
        for button in self.mouse_palette.palette_buttons:  # get trace palette
            self.series.palette_traces.append(button.trace)
            if button.isChecked():
                self.series.current_trace = button.trace
        self.field.section.save()
        self.series.save()
    
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
        
        HistoryWidget(self, output_str)
    
    def openObjectList(self):
        """Open the object list widget."""
        self.saveAllData()
        self.field.openObjectList()
    
    def openZtraceList(self):
        """Open the ztrace list widget."""
        self.saveAllData()
        self.field.openZtraceList()
    
    def openTraceList(self):
        """Open the trace list widget."""
        self.field.openTraceList()
    
    def openSectionList(self):
        """Open the section list widget."""
        self.field.openSectionList()
    
    def setToObject(self, obj_name : str, section_num : str):
        """Focus the field on an object from a specified section.
        
            Params:
                obj_name (str): the name of the object
                section_num (str): the section the object is located
        """
        self.changeSection(section_num)
        self.field.findContour(obj_name)
    
    def changeTform(self):
        """Open a dialog to change the transform of a section."""
        # check for section locked status
        if self.field.section.align_locked:
            return
        
        current_tform = " ".join(
            [str(round(n, 5)) for n in self.field.section.tforms[self.series.alignment].getList()]
        )
        new_tform, confirmed = QInputDialog.getText(
            self, "New Transform", "Enter the desired section transform:", text=current_tform)
        if not confirmed:
            return
        try:
            new_tform = [float(n) for n in new_tform.split()]
            if len(new_tform) != 6:
                return
        except ValueError:
            return
        self.field.changeTform(Transform(new_tform))
    
    def translate(self, direction : str, amount : str):
        """Translate the current transform.
        
            Params:
                direction (str): left, right, up, or down
                amount (str): small, med, or big
        """
        if amount == "small":
            num = self.smallnum
        elif amount == "med":
            num = self.mednum
        elif amount == "big":
            num = self.bignum
        if direction == "left":
            x, y = -num, 0
        elif direction == "right":
            x, y = num, 0
        elif direction == "up":
            x, y = 0, num
        elif direction == "down":
            x, y = 0, -num
        self.field.translate(x, y)
    
    def gotoSection(self):
        """Open a dialog to jump to a specific section number."""
        new_section_num, confirmed = QInputDialog.getText(
            self, "Go To Section", "Enter the desired section number:", text=str(self.series.current_section))
        if not confirmed:
            return
        try:
            new_section_num = int(new_section_num)
            self.changeSection(new_section_num)
        except ValueError:
            return
    
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
    
    def changeAlignment(self):
        """Switch alignments."""
        alignments = list(self.field.section.tforms.keys())
        alignment_name, confirmed = AlignmentDialog(
            self,
            alignments
        ).exec()
        if not confirmed:
            return
        
        if alignment_name not in alignments:
            self.newAlignment()

        self.field.changeAlignment(alignment_name)

    def closeEvent(self, event):
        """Save all data to files when the user exits."""
        if not self.field: # do not do anything if field is not created
            event.accept()
            return
        self.saveAllData()
        event.accept()
