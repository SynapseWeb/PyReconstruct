import os
from time import time

from PySide6.QtWidgets import (QMainWindow, QFileDialog,
    QInputDialog, QApplication,
    QMessageBox)
from PySide6.QtGui import QKeySequence, QShortcut

from modules.gui.objecttablewidget import ObjectTableWidget
from modules.gui.mousedockwidget import MouseDockWidget
from modules.gui.fieldwidget import FieldWidget

from modules.backend.xml_json_conversions import xmlToJSON, jsonToXML
from modules.backend.import_transforms import importTransforms

from modules.pyrecon.series import Series

from modules.autoseg.zarrtorecon import saveZarrImages, importZarrObjects

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
        self.mouse_dock = None  # placeholder for mouse dock
        self.obj_list = None  # placeholder for object list
        self.setMouseTracking(True) # set constant mouse tracking for various mouse modes
        # number defaults
        self.smallnum = 0.01
        self.mednum = 0.1
        self.bignum = 1

        # create status bar at bottom of window
        self.statusbar = self.statusBar()

        # open series and create field
        welcome_series = Series(assets_dir + "/welcome_series/welcome.ser")
        self.openSeries(welcome_series, refresh_menu=False)
        self.field.generateView()

        # create menu and shortcuts
        self.createMenu()
        self.createShortcuts()

        self.show()

    def createMenu(self):
        # menu at top of window
        self.menubar = self.menuBar()

        if self.series.filetype == "XML":
            outtype = "JSON"
        elif self.series.filetype == "JSON":
            outtype = "XML"

        menu_options = [
            
            {
                "attribute": "filemenu",
                "name": "File",
                "opts":
                [
                    ("new_act", "New", "Ctrl+N", self.newSeries),
                    ("open_act", "Open", "", self.openSeries),
                    ("export_series_act", f"Export series to {outtype}...", "", self.exportSeries),
                    ("import_transforms_act", "Import transformations...", "", self.importTransforms),
                    ("new_from_zarr_act", "New from zarr file", "", self.newSeriesFromZarr),
                    ("import_from_zarr_act", "Import objects from zarr...", "", self.importZarrObjects)
                ]
             },

            {
                "attribute": "seriesmenu",
                "name": "Series",
                "opts":
                [
                    ("change_src_act", "Change image directory...", "", self.changeSrcDir)
                ]
             },
            
            {
                "attribute": "objectmenu",
                "name": "Objects",
                "opts":
                [
                    ("objectlist_act", "Open object list", "Ctrl+Shift+O", self.openObjectList)
                ]
             },

            {
                "attribute": "alignmentmenu",
                "name": "Alignment",
                "opts":
                [
                    ("newalignment_act", "New alignment", "", self.newAlignment),
                    ("switchalignment_act", "Switch alignment", "Ctrl+Shift+A", self.switchAlignment)
                ]
             }
        ]

        # Populate menu bar with menus and options
        for menu in menu_options:
            # Create menu
            setattr(self, menu.get('attribute'), self.menubar.addMenu(menu.get('name')))
            current_menu = getattr(self, menu.get('attribute'))
            # Add menu options
            for act, text, kbd, f in menu.get('opts'):
                setattr(self, act, current_menu.addAction(text))
                menu_self = getattr(self, act)
                menu_self.setShortcut(kbd)
                menu_self.triggered.connect(f)

    def createShortcuts(self):
        # create shortcuts
        shortcuts = [
            ("Ctrl+S", self.saveAllData),
            ("Ctrl+M", self.field.mergeSelectedTraces),
            ("Ctrl+D", self.field.deselectAllTraces),
            ("Ctrl+H", self.field.hideSelectedTraces),
            ("Ctrl+Shift+H", self.field.toggleHideAllTraces),
            ("Ctrl+Z", self.field.undoState),
            ("Ctrl+Y", self.field.redoState),
            ("Ctrl+T", self.changeTform),
            ("Ctrl+G", self.gotoSection),
            ("Ctrl+A", self.field.changeTraceAttributes),
            # translate motions
            ("Ctrl+Left", lambda : self.translateTform("left", "small")),
            ("Shift+Left", lambda : self.translateTform("left", "med")),
            ("Ctrl+Shift+Left", lambda : self.translateTform("left", "big")),
            ("Ctrl+Right", lambda : self.translateTform("right", "small")),
            ("Shift+Right", lambda : self.translateTform("right", "med")),
            ("Ctrl+Shift+Right", lambda : self.translateTform("right", "big")),
            ("Ctrl+Up", lambda : self.translateTform("up", "small")),
            ("Shift+Up", lambda : self.translateTform("up", "med")),
            ("Ctrl+Shift+Up", lambda : self.translateTform("up", "big")),
            ("Ctrl+Down", lambda : self.translateTform("down", "small")),
            ("Shift+Down", lambda : self.translateTform("down", "med")),
            ("Ctrl+Shift+Down", lambda : self.translateTform("down", "big")),
        ]
        
        for kbd, act in shortcuts:
            if type(act) is tuple:
                sc = QShortcut(QKeySequence(kbd), self)
                for func in act:
                    sc.activated.connect(func)
            else:
                QShortcut(QKeySequence(kbd), self).activated.connect(act)
    
    def changeSrcDir(self, notify=False):
        """Open a series of dialogs to change the image source directory."""
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
        if not notify:
            self.field.reloadImage()
    
    def openSeries(self, series_obj=None, refresh_menu=True):
        """Open an existing series and create the field.
        
            Params:
                series_obj (Series): the series object (optional)
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

        # create mouse dock
        if self.mouse_dock is not None: # close previous mouse dock
            self.mouse_dock.close()
        self.mouse_dock = MouseDockWidget(self.series.palette_traces, self.series.current_trace, self)
        self.changeTracingTrace(self.series.current_trace) # set the current trace

        if self.obj_list is not None:
            self.obj_list.close()
            self.obj_list = None

        # refresh export choice on menu
        if refresh_menu:
            if self.series.filetype == "XML":
                outtype = "JSON"
            elif self.series.filetype == "JSON":
                outtype = "XML"
            export_series_act = getattr(self, "export_series_act")
            export_series_act.setText(f"Export series to {outtype}...")
    
    def newSeries(self, image_locations : list):
        """Create a new series from a set of images."""
        # get images from user
        if not image_locations:
            image_locations, extensions = QFileDialog.getOpenFileNames(
                self, "Select Images", filter="*.jpg *.jpeg *.png *.tif *.tiff")
            if len(image_locations) == 0:
                return
        # get the name of the series from user
        series_name, confirmed = QInputDialog.getText(
            self, "Series Name", "What is the name of this series?")
        if not confirmed:
            return
        # get calibration (microns per pix) from user
        mag, confirmed = QInputDialog.getDouble(
            self, "Section Calibration", "What is the calibration for this series?",
            0.00254, minValue=0.000001, decimals=6)
        if not confirmed:
            return
        # get section thickness (microns) from user
        thickness, confirmed = QInputDialog.getDouble(
            self, "Section Thickness", "What is the section thickness for this series?",
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
        """Export the series to a given filetype.
        
            Params:
                outtype (str): XML or JSON
        """
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

    def importZarrObjects(self, zarr_fp : str):  # MIGRATE TO BACKEND
        """Import objects from a zarr folder."""
        self.saveAllData()
        # get the file path
        if not zarr_fp:
            zarr_fp = QFileDialog.getExistingDirectory(self, "Select Zarr Folder")
            if not zarr_fp:
                return
        importZarrObjects(self, self.series, zarr_fp)
        self.field.reload()
    
    def newSeriesFromZarr(self):
        zarr_fp = QFileDialog.getExistingDirectory(self, "Select Zarr Folder")
        if not zarr_fp:
            return
        save_fp = QFileDialog.getExistingDirectory(self, "Select Folder for New Series")
        if not save_fp:
            return
        image_locations = saveZarrImages(zarr_fp, save_fp)
        self.newSeries(image_locations)
        self.importZarrObjects(zarr_fp)
    
    def changeMouseMode(self, new_mode):
        """Change the mouse mode of the field (pointer, panzoom, tracing...).

        Called when user clicks on mouse mode palette.
        """
        self.field.setMouseMode(new_mode)

    def changeTracingTrace(self, trace):
        """Change the trace utilized by the user.

        Called when user clicks on trace palette.
        """
        self.series.current_trace = trace
        self.field.setTracingTrace(trace)
    
    def changeSection(self, section_num, save=True):
        """Change the section of the field."""
        start_time = time()
        # save data
        if save:
            self.saveAllData()
        # change the field section
        self.field.changeSection(section_num)
        # update status bar
        self.field.updateStatusBar()
        print("Time taken to change section:", time() - start_time, "sec")
    
    def keyPressEvent(self, event):
        """Called when any key is pressed and user focus is on main window."""
        if not self.field:  # do not respond to keyboard if field is not created
            return
        if event.key() == 16777238:  # PgUp
            section_numbers = sorted(list(self.series.sections.keys()))  # get list of all section numbers
            section_number_i = section_numbers.index(self.series.current_section)  # get index of current section number in list
            if section_number_i < len(section_numbers) - 1:
                self.changeSection(section_numbers[section_number_i + 1])
        elif event.key() == 16777239:  # PgDn
            section_numbers = sorted(list(self.series.sections.keys()))  # get list of all section numbers
            section_number_i = section_numbers.index(self.series.current_section)  # get index of current section number in list
            if section_number_i > 0:
                self.changeSection(section_numbers[section_number_i - 1])
        elif event.key() == 16777223:  # Del
            self.field.deleteSelectedTraces()
        elif event.key() == 45:  # -
            self.field.changeBrightness(-5)
        elif event.key() == 61:  # +
            self.field.changeBrightness(5)
        elif event.key() == 91: # [
            self.field.changeContrast(-0.2)
        elif event.key() == 93: # ]
            self.field.changeContrast(0.2)
        elif event.key() == 32: # Space
            self.field.toggleBlend()
        # print(event.key())  # developer purposes
    
    def wheelEvent(self, event):
        """Called when mouse scroll is used."""
        if not self.field:  # do not respond to mouse wheel if field is not created
            return
        section_numbers = list(self.series.sections.keys())  # get list of all section numbers
        section_number_i = section_numbers.index(self.series.current_section)  # get index of current section number in list
        if event.angleDelta().y() > 0:  # if scroll up
            if section_number_i < len(section_numbers) - 1:
                self.changeSection(section_numbers[section_number_i + 1])
        elif event.angleDelta().y() < 0:  # if scroll down
            if section_number_i > 0:
                self.changeSection(section_numbers[section_number_i - 1])
    
    def saveAllData(self):
        """Write current series and section data into JSON files."""
        # save the trace palette
        self.series.palette_traces = []
        for button in self.mouse_dock.palette_buttons:  # get trace palette
            self.series.palette_traces.append(button.trace)
            if button.isChecked():
                self.series.current_trace = button.trace
        self.field.section.save()
        self.series.save()
        if self.obj_list is not None and self.obj_list.isVisible():  # update the table if present
            self.obj_list.updateSectionData(self.series.current_section, self.field.section)
    
    def openObjectList(self):
        """Open the object list widget."""
        self.saveAllData()
        # current placeholder until options widget is created
        quantities = {}
        quantities["range"] = True
        quantities["count"] = True
        quantities["surface_area"] = False
        quantities["flat_area"] = True
        quantities["volume"] = True
        self.obj_list = ObjectTableWidget(self.series, quantities, self)
    
    def setToObject(self, obj_name : str, section_num : str):
        """Focus the field on an object from a specified section.
        
            Params:
                obj_name (str): the name of the object
                section_num (str): the section the object is located
        """
        self.changeSection(section_num)
        self.field.findTrace(obj_name)
    
    def changeTform(self):
        """Open a dialog to change the transform of a section."""
        current_tform = " ".join(
            [str(round(n, 2)) for n in self.field.section.tforms[self.series.alignment]]
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
        self.field.changeTform(new_tform)
    
    def translateTform(self, direction : str, amount : str):
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
        new_tform = self.field.section.tforms[self.series.alignment].copy()
        new_tform[2] += x
        new_tform[5] += y
        self.field.changeTform(new_tform)
    
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
    
    def newAlignment(self):
        """Add a new alignment."""
        new_alignment_name, confirmed = QInputDialog.getText(
            self,
            "New Alignment",
            "Enter the name for your new alignment:"
        )
        if not confirmed:
            return
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
        self.field.reload()
        self.field.changeAlignment(new_alignment_name)
    
    def switchAlignment(self):
        """Switch alignments."""
        alignment_name, confirmed = QInputDialog.getText(
            self,
            "Switch Alignment",
            "Enter the alignment name:"
        )
        if not confirmed:
            return
        if alignment_name not in self.field.section.tforms:
            QMessageBox.information(
                self,
                " ",
                "This alignment does not exist.",
                QMessageBox.Ok
            )
            return
        self.field.changeAlignment(alignment_name)

    def closeEvent(self, event):
        """Save all data to files when the user exits."""
        if not self.field: # do not do anything if field is not created
            event.accept()
            return
        self.saveAllData()
        event.accept()
