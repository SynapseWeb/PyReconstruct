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
from constants.defaults import getDefaultPaletteTraces


def my_example(arg):
    print(arg)

class MainWindow(QMainWindow):

    def __init__(self):
        """Constructs the skeleton for an empty main window."""
        super().__init__() # run QMainWindow init function
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
        self.obj_list = None
        self.setMouseTracking(True) # set constant mouse tracking for various mouse modes

        # create status bar (at bottom of window)
        self.statusbar = self.statusBar()

        # open the series and create the field
        self.openSeries(assets_dir + "/welcome_series/welcome.ser")
        # reset welcome window view
        self.field.current_window = [0,0,1,1]
        self.field.generateView()
        self.field.update()

        # menu at top of window
        self.menubar = self.menuBar()

        # file menu
        self.filemenu = self.menubar.addMenu("File")
        self.new_act = self.filemenu.addAction("New")  # create a new series
        self.new_act.setShortcut("Ctrl+N")
        self.new_act.triggered.connect(self.newSeries)
        self.open_act = self.filemenu.addAction("Open")  # open an existing series
        self.open_act.triggered.connect(self.openSeries)
        self.import_transforms = self.filemenu.addAction("Import transforms...")
        self.import_transforms.triggered.connect(self.importTransforms)
        self.new_from_xml_act = self.filemenu.addAction("New from xml series")  # create a new series from XML Reconstruct data
        self.new_from_xml_act.triggered.connect(self.newSeriesFromXML)
        self.new_from_zarr_act = self.filemenu.addAction("New from zarr file")
        self.new_from_zarr_act.triggered.connect(self.newSeriesFromZarr)
        self.export_to_xml_act = self.filemenu.addAction("Export traces to XML...")
        self.export_to_xml_act.triggered.connect(self.exportTracesToXML)
        self.import_from_json_act = self.filemenu.addAction("Import objects from zarr...")
        self.import_from_json_act.triggered.connect(self.importZarrObjects)
        # object menu
        self.objectmenu = self.menubar.addMenu("Object")
        self.objectlist_act = self.objectmenu.addAction("Open object list")
        self.objectlist_act.triggered.connect(self.openObjectList)

        # create shortcuts
        save_sc = QShortcut(QKeySequence("Ctrl+S"), self)
        save_sc.activated.connect(self.saveAllData)
        merge_sc = QShortcut(QKeySequence("Ctrl+M"), self)
        merge_sc.activated.connect(self.field.mergeSelectedTraces)
        deselect_sc = QShortcut(QKeySequence("Ctrl+D"), self)
        deselect_sc.activated.connect(self.field.deselectAllTraces)
        hide_sc = QShortcut(QKeySequence("Ctrl+H"), self)
        hide_sc.activated.connect(self.field.hideSelectedTraces)
        hideall_sc = QShortcut(QKeySequence("Ctrl+Shift+H"), self)
        hideall_sc.activated.connect(self.field.toggleHideAllTraces)
        undo_sc = QShortcut(QKeySequence("Ctrl+Z"), self)
        undo_sc.activated.connect(self.field.undoState)
        redo_sc = QShortcut(QKeySequence("Ctrl+Y"), self)
        redo_sc.activated.connect(self.field.redoState)
        change_tform_sc = QShortcut(QKeySequence("Ctrl+T"), self)
        change_tform_sc.activated.connect(self.changeTform)

        ########### TESTING #####################################
        # Example shortcut
        example_sc = QShortcut(QKeySequence("Ctrl+G"), self)
        ### example_sc.activated.connect(self.series.section)

        self.show()
    
    def openSeries(self, series_fp=""):
        """Open an existing series and create the field.
        
            Params:
                series_fp (str): series filepath (optional)
        """
        if series_fp:  # if series is provided (only the case if opening from new)
            self.series = Series(series_fp)
        else:  # get series file from user
            series_fp, extension = QFileDialog.getOpenFileName(self, "Select Series", filter="*.ser")
            if series_fp == "": return  # exit function if user does not provide series
            self.series = Series(series_fp)  # load series data into Series object
        self.series_fp = series_fp

        # get working directory as series location
        if "/" in series_fp:
            self.wdir = series_fp[:series_fp.rfind("/")+1]

        # create the FieldWidget object and set as main widget
        if self.series.current_section not in self.series.sections:  # if last known section number is not valid
            self.series.current_section = list(self.series.sections.keys())[0]
        self.section = Section(self.wdir + self.series.sections[self.series.current_section])
        if self.field is None: # create field widget if not already
            self.field = FieldWidget(self.series.current_section, self.section, self.series.window, self)
            self.setCentralWidget(self.field)
        else:
            self.field.loadSeries(self.series.current_section, self.section, self.series.window)

        # create mouse dock
        if self.mouse_dock is not None: # close if one exists
            self.mouse_dock.close()
        self.mouse_dock = MouseDockWidget(self.series.palette_traces, self.series.current_trace, self)
        self.changeTracingTrace(self.series.current_trace) # set the current trace
    
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
        
        # create series data file (.ser)
        series_data = {}
        series_data["sections"] = {}  # section_number : section_filename
        series_data["current_section"] = 0  # last section left off
        series_data["window"] = [0, 0, 1, 1] # x, y, w, h of reconstruct window in field coordinates
        for i in range(len(image_locations)):
            series_data["sections"][i] = series_name + "." + str(i)
        series_data["palette_traces"] = getDefaultPaletteTraces()  # trace palette
        series_data["current_trace"] = series_data["palette_traces"][0]
        with open(self.wdir + series_name + ".ser", "w") as series_file:
            series_file.write(json.dumps(series_data, indent=2))
        
        # create section files (.#)
        for i in range(len(image_locations)):
            section_data = {}
            section_data["src"] = image_locations[i][image_locations[i].rfind("/")+1:]  # image location
            section_data["mag"] = mag  # microns per pixel
            section_data["thickness"] = thickness  # section thickness
            section_data["tform"] = [1, 0, 0, 0, 1, 0]  # identity matrix default
            section_data["traces"] = []
            with open(self.wdir + series_name + "." + str(i), "w") as section_file:
                section_file.write(json.dumps(section_data, indent=2))
    
        # open series after creating
        self.openSeries(self.wdir + series_name + ".ser")
    
    def newSeriesFromXML(self):
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
                mode = contour.mode  # not used in pyReconstruct, but useful to store for exporting back to XML
                new_trace = Trace(name, color, closed=closed, mode=mode)
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
    
    def importTransforms(self):
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

    def importZarrObjects(self, zarr_fp : str):
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
    
    def randomColor(self):
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
        if section_num not in self.series.sections:  # check if requested section exists
            return
        if save:
            self.saveAllData()
        self.series.current_section = section_num
        self.section = Section(self.wdir + self.series.sections[self.series.current_section])
        self.field.loadSection(self.series.current_section, self.section)
        print("Time taken to change section:", time() - start_time, "sec")
    
    def keyPressEvent(self, event):
        """Called when any key is pressed and user focus is on main window."""
        if not self.field:  # do not respond to keyboard if field is not created
            return
        section_numbers = list(self.series.sections.keys())  # get list of all section numbers
        section_number_i = section_numbers.index(self.series.current_section)  # get index of current section number in list
        if event.key() == 16777238:  # if PgUp is pressed
            if section_number_i < len(section_numbers) - 1:
                self.changeSection(section_numbers[section_number_i + 1])
        elif event.key() == 16777239:  # if PgDn is pressed
            if section_number_i > 0:
                self.changeSection(section_numbers[section_number_i - 1])
        elif event.key() == 16777223:  # if Del is pressed
            self.field.deleteSelectedTraces()
        elif event.key() == 45:  # if - is pressed
            self.field.changeBrightness(-1)
        elif event.key() == 61:  # if + is pressed
            self.field.changeBrightness(1)
    
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
        self.section.traces = self.field.traces  # get traces from field
        self.series.window = self.field.current_window  # get window view
        self.series.palette_traces = []
        for button in self.mouse_dock.palette_buttons:  # get trace palette
            self.series.palette_traces.append(button.trace)
            if button.isChecked():
                self.series.current_trace = button.trace
        self.section.save()
        self.series.save()
        if self.obj_list is not None and self.obj_list.isVisible():  # update the table if present
            self.obj_list.updateSectionData(self.series.current_section, self.section)
    
    def openObjectList(self):
        """Open the object list widget."""
        self.saveAllData()
        # current placeholder until options widget is created
        quantities = {}
        quantities["range"] = False
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
    
    def exportTracesToXML(self):
        """Export all traces to existing XML series.
        
        This function overwrites the traces in the XML series.
        """
        self.saveAllData()
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
                    mode = trace.mode,
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
        current_tform = " ".join([str(round(n, 2)) for n in self.section.tform])
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
        self.section.tform = new_tform
        self.field.loadTransformation(new_tform, update=True, save_state=True)
        
    def closeEvent(self, event):
        """Save all data to files when the user exits."""
        if not self.field: # do not do anything if field is not created
            event.accept()
            return
        self.saveAllData()
        event.accept()
