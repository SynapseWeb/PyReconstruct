import json
import os
from time import time
import random

from PySide6.QtWidgets import (QMainWindow, QFileDialog,
    QInputDialog, QApplication, QProgressDialog,
    QMessageBox)
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import Qt

from modules.gui.objecttablewidget import ObjectTableWidget
from modules.gui.mousedockwidget import MouseDockWidget
from modules.gui.fieldwidget import FieldWidget

from modules.recon.series import Series
from modules.recon.section import Section
from modules.recon.trace import Trace

from modules.pyrecon.utils.reconstruct_reader import process_series_directory
from modules.pyrecon.utils.reconstruct_writer import write_series
from modules.pyrecon.classes.contour import Contour
from modules.pyrecon.classes.transform import Transform as XMLTransform

from modules.autoseg.zarrtorecon import getZarrObjects, saveZarrImages

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

        # create status bar at bottom of window
        self.statusbar = self.statusBar()

        # open series and create field
        welcome_series = Series(assets_dir + "/welcome_series/welcome.ser")
        self.openSeries(welcome_series)
        self.field.generateView()

        # create menu and shortcuts
        self.createMenu()
        self.createShortcuts()

        self.show()

    def createMenu(self):
        # menu at top of window
        self.menubar = self.menuBar()

        menu_options = [
            
            {
                "attribute": "filemenu",
                "name": "File",
                "opts":
                [
                    ("new_act", "New", "Ctrl+N", self.newSeries),
                    ("open_act", "Open", "", self.openSeries),
                    ("import_transforms_act", "Import transformations...", "", self.importTransforms),
                    ("new_from_xml_act", "New from XML series...", "", self.newSeriesFromXML),
                    ("new_from_zarr_act", "New from zarr file", "", self.newSeriesFromZarr),
                    ("export_to_xml_act", "Export traces to XML...", "", self.exportTracesToXML),
                    ("import_from_zarr_act", "Import objects from zarr...", "", self.importZarrObjects)
                ]
             },

            {
                "attribute": "seriesmenu",
                "name": "Series",
                "opts":
                [
                    ("change_src_act", "Change Image Directory", "", self.field.changeSrcDir)
                ]
             },
            
            {
                "attribute": "objectmenu",
                "name": "Objects",
                "opts":
                [
                    ("objectlist_act", "Open object list", "Ctrl+Shift+O", self.openObjectList)
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
            ("Ctrl+A", self.field.changeTraceAttributes)
        ]
        
        for kbd, act in shortcuts:
            if type(act) is tuple:
                sc = QShortcut(QKeySequence(kbd), self)
                for func in act:
                    sc.activated.connect(func)
            else:
                QShortcut(QKeySequence(kbd), self).activated.connect(act)
    
    def openSeries(self, series_obj=None):
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
    
    def newSeriesFromXML(self):  # MIGRATE TO BACKEND
        """Create a new series from existing XML series data."""
        # get the XML file location from the user
        xml_file, ext = QFileDialog.getOpenFileName(self, "Open the XML SER file", filter="*.ser")
        if not xml_file:
            return
        xml_dir = xml_file[:xml_file.rfind("/")]
        # get the intended location for the new JSON files
        json_dir = QFileDialog.getExistingDirectory(self, "Select folder to contain JSON files")
        if not json_dir:
            return
        
        # load all the XML series data
        progbar = QProgressDialog("Loading XML series...", "Cancel", 0, 100, self)
        progbar.setWindowTitle("Open XML Series")
        progbar.setWindowModality(Qt.WindowModal)
        series = process_series_directory(xml_dir, progbar=progbar)

        # create new series JSON file
        series_data = {}
        series_data["sections"] = {}
        series_data["current_section"] = 0
        series_data["src_dir"] = ""
        series_data["window"] = [0, 0, 1, 1]
        series_data["palette_traces"] = []
        for contour in series.contours:  # import XML trace palette
            name = contour.name
            color = list(contour.border)
            for i in range(len(color)):
                color[i] *= 255
            new_trace = Trace(name, color)
            new_trace.points = contour.points
            series_data["palette_traces"].append(new_trace.getDict())
        series_data["current_trace"] = series_data["palette_traces"][0]

        # import data from each XML section file
        progbar = QProgressDialog("Importing series data...", "Cancel", 0, 100, self)
        progbar.setWindowTitle("Import XML Data")
        progbar.setWindowModality(Qt.WindowModal)
        prog_value = 0
        final_value = len(series.sections)
        for n, section in sorted(series.sections.items()):
            series_data["sections"][n] = section.name  # add section name to series file data
            section_data = {}
            image = section.images[0]
            section_data["src"] = image.src
            section_data["brightness"] = 0
            section_data["contrast"] = 0
            section_data["mag"] = image.mag
            section_data["thickness"] = section.thickness
            transform = image.transform
            forward_transform = transform.tform()  # get the forward transform 3x3 numpy matrix
            ft = forward_transform  # just to make it easier to index in next line
            section_data["tform"] = (ft[0, 0], ft[0, 1], ft[0, 2], ft[1, 0], ft[1, 1], ft[1, 2])
            section_data["traces"] = []
            for contour in section.contours:  # iterate through all contours
                name = contour.name
                color = list(contour.border)
                for i in range(len(color)):
                    color[i] *= 255
                closed = contour.closed
                new_trace = Trace(name, color, closed=closed)
                points = contour.points
                points = contour.transform.transformPoints(points)  # transform points by its own contour (get field points)
                points = transform.inverseTransformPoints(points)  # reverse transform points by image transform (fix points to image)
                new_trace.points = points
                section_data["traces"].append(new_trace.getDict())
            with open(json_dir + "/" + section.name, "w") as section_file:
                section_file.write(json.dumps(section_data, indent=2))
            if progbar.wasCanceled(): return  # cancel function if user hits cancel during loading
            prog_value += 1
            progbar.setValue(prog_value / final_value * 100)

        # save series file
        series_fp = json_dir + "/" + series.name + ".ser"
        with open(series_fp, "w") as series_file:
                series_file.write(json.dumps(series_data, indent=2))
        self.openSeries(series_fp)
    
    def importTransforms(self):  # MIGRATE TO BACKEND
        """Import transforms from a text file."""
        self.saveAllData()
        # get file from user
        tforms_file, ext = QFileDialog.getOpenFileName(self, "Select file containing transforms")
        if not tforms_file:
            return
        # read through file
        with open(tforms_file, "r") as f:
            lines = f.readlines()
        tforms = {}
        for line in lines:
            nums = line.split()
            if len(nums) != 7:
                print("Incorrect transform file format")
                return
            try:
                if int(nums[0]) not in self.series.sections:
                    print("Transform file section numbers do not correspond to this series")
                    return
                tforms[int(nums[0])] = [float(n) for n in nums[1:]]
            except ValueError:
                print("Incorrect transform file format")
                return
        # set tforms
        for section_num, tform in tforms.items():
            section = Section(self.wdir + self.series.sections[int(section_num)])
            # multiply pixel translations by magnification of section
            tform[2] *= section.mag
            tform[5] *= section.mag
            section.tform = tform
            section.save()
        # reload current section
        self.changeSection(self.series.current_section, save=False)

    def importZarrObjects(self, zarr_fp : str):  # MIGRATE TO BACKEND
        """Import objects from a zarr folder."""
        self.saveAllData()
        # get the file path
        if not zarr_fp:
            zarr_fp = QFileDialog.getExistingDirectory(self, "Select Zarr Folder")
            if not zarr_fp:
                return
        # retrieve objects from zarr
        progbar = QProgressDialog("Loading Zarr data...", "Cancel", 0, 100, self)
        progbar.setWindowTitle("Zarr Data")
        progbar.setWindowModality(Qt.WindowModal)
        objects = getZarrObjects(zarr_fp, progbar=progbar)
        # assign random colors to each id
        color_dict = {}
        for id in objects:
            color_dict[id] = self.randomColor()
        # import loaded zarr objects
        progbar = QProgressDialog("Importing objects...", "Cancel", 0, 100, self)
        progbar.setWindowTitle("Load objects")
        progbar.setWindowModality(Qt.WindowModal)
        final_value = len(self.series.sections.keys())
        progress = 0
        for section_num in self.series.sections:
            section = Section(self.wdir + self.series.sections[int(section_num)])
            for id, traces in objects.items():
                if section_num in traces.keys():
                    for trace in traces[section_num]:
                        new_trace = Trace(str(id), color_dict[id])
                        new_trace.points = trace
                        section.traces.append(new_trace)
                        if section_num == self.series.current_section:
                            self.field.traces.append(new_trace)
            section.save()
            if progbar.wasCanceled():
                return
            else:
                progress += 1
                progbar.setValue(progress/final_value * 100)
        self.field.saveState()
        self.field.generateView(generate_image=False)
        self.field.update()
    
    def newSeriesFromZarr(self):  # MIGRATE TO BACKEND
        zarr_fp = QFileDialog.getExistingDirectory(self, "Select Zarr Folder")
        if not zarr_fp:
            return
        save_fp = QFileDialog.getExistingDirectory(self, "Select Folder for New Series")
        if not save_fp:
            return
        image_locations = saveZarrImages(zarr_fp, save_fp)
        self.newSeries(image_locations)
        self.importZarrObjects(zarr_fp)
    
    def randomColor(self):  # MIGRATE TO BACKEND
        """Returns a random primary or secondary color.
        
            Returns:
                (tuple): color (255,255,255)
        """
        n = random.randint(1,5)
        if n == 1: return (0,255,0)
        elif n == 2: return (0,255,255)
        elif n == 3: return (255,0,0)
        elif n == 4: return (255,0,255)
        elif n == 5: return (255,255,0)
    
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
        print(event.key())  # developer purposes
    
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
        self.obj_list = ObjectTableWidget(self.series, self.wdir, quantities, self)
    
    def setToObject(self, obj_name : str, section_num : str):
        """Focus the field on an object from a specified section.
        
            Params:
                obj_name (str): the name of the object
                section_num (str): the section the object is located
        """
        self.changeSection(section_num)
        self.field.findTrace(obj_name)
    
    def exportTracesToXML(self):  # MIGRATE TO BACKEND
        """Export all traces to existing XML series.
        
        This function overwrites the traces in the XML series.
        """
        self.saveAllData()
        
        # check series filetype
        if self.series.filetype == "XML":
            QMessageBox.information(
                self,
                "Series Filetype",
                "Series is already in XML format.",
                QMessageBox.Ok
            )
            return

        # warn the user about overwriting the XML traces
        warn = QMessageBox()
        warn.setIcon(QMessageBox.Warning)
        warn.setText("WARNING: All traces on the XML file will be overwritten.")
        warn.setInformativeText("Backing up is suggested.")
        warn.setWindowTitle("Warning")
        warn.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        response = warn.exec_()
        if response == QMessageBox.Cancel:
            return
        
        # get the XML file from the user
        xml_file, ext = QFileDialog.getOpenFileName(self, "Locate the XML SER file", filter="*.ser")
        if not xml_file:
            return
        xml_dir = xml_file[:xml_file.rfind("/")]
        # load the XML series file data
        progbar = QProgressDialog("Loading XML series...", "Cancel", 0, 100, self)
        progbar.setWindowTitle("Open XML Series")
        progbar.setWindowModality(Qt.WindowModal)
        xml_series = process_series_directory(xml_dir, progbar=progbar)
    
        # export the tracesin the JSON files to the XML file data
        progbar = QProgressDialog("Exporting new traces...", "Cancel", 0, 100, self)
        progbar.setWindowTitle("Export to XML Series")
        progbar.setWindowModality(Qt.WindowModal)
        prog_value = 0
        final_value = len(self.series.sections)
        for section_num, section_name in self.series.sections.items():
            section = Section(self.wdir + section_name)
            xml_series.sections[section_num].contours = []  # clear the list of XML file contours
            for trace in section.traces:
                contour_color = list(trace.color)  # get trace color
                for i in range(len(contour_color)):
                    contour_color[i] /= 255
                tf = section.tform
                xcoef = (tf[2], tf[0], tf[1])
                ycoef = (tf[5], tf[3], tf[4])
                transform = XMLTransform(xcoef=xcoef, ycoef=ycoef).inverse  # invert transform
                new_contour = Contour(
                    name = trace.name,
                    comment = "",
                    hidden = False,
                    closed = trace.closed,
                    simplified = True,
                    mode = 11,
                    border = contour_color,
                    fill = contour_color,  # the fill is set as border color
                    points = trace.points,
                    transform = transform
                )
                xml_series.sections[section_num].contours.append(new_contour)  # add the new contour to XML data
                if progbar.wasCanceled(): return
                prog_value += 1
                progbar.setValue(prog_value / final_value * 100)
        
        # write modified XML data to XML files
        progbar = QProgressDialog("Writing to XML series...", "Cancel", 0, 100, self)
        progbar.setWindowTitle("Write XML Series")
        progbar.setWindowModality(Qt.WindowModal)
        write_series(xml_series, xml_dir, sections=True, overwrite=True, progbar=progbar)
    
    def changeTform(self):
        """Open a dialog to change the transform of a section."""
        current_tform = " ".join([str(round(n, 2)) for n in self.field.section.tform])
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
        
    def closeEvent(self, event):
        """Save all data to files when the user exits."""
        if not self.field: # do not do anything if field is not created
            event.accept()
            return
        self.saveAllData()
        event.accept()
