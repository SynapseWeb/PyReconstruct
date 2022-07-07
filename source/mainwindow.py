import os
import json
from PySide2.QtWidgets import (QMainWindow, QFileDialog,
    QInputDialog, QShortcut, QApplication)
from PySide2.QtGui import (QKeySequence)
from objecttablewidget import ObjectTableWidget
from mousedockwidget import MouseDockWidget

from fieldwidget import FieldWidget
from series import Series
from section import Section
from trace import Trace

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("pyReconstruct")

        self.menubar = self.menuBar()
        self.filemenu = self.menubar.addMenu("File")
        self.new_act = self.filemenu.addAction("New")
        self.new_act.setShortcut("Ctrl+N")
        self.new_act.triggered.connect(self.newSeries) # create a new series
        self.new_act
        self.open_act = self.filemenu.addAction("Open")
        self.open_act.triggered.connect(self.openSeries) # open an existing series

        self.field = None
        self.setMouseTracking(True)
        self.setGeometry(100, 100, 500, 500)
        self.show()
    
    def newSeries(self):
        """Create a new series from a set of images"""
        # get images from user
        image_locations, extensions = QFileDialog.getOpenFileNames(self, "Select Images", filter="*.jpg *.jpeg *.png *.tif *.tiff")
        if len(image_locations) == 0:
            return
        
        # get the name of the series from user
        series_name, confirmed = QInputDialog.getText(self, "Series Name", "What is the name of this series?")
        if not confirmed:
            return
        
        # get calibration (microns per pix) from user
        mag, confirmed = QInputDialog.getDouble(self, "Section Calibration",
                                                "What is the calibration for this series?",
                                                0.00254, minValue=0.000001, decimals=6)

        # get section thickness (microns) from user
        thickness, confirmed = QInputDialog.getDouble(self, "Section Thickness",
                                                "What is the section thickness for this series?",
                                                0.05, minValue=0.000001, decimals=6)

        if not confirmed:
            return
        
        # change working directory to folder with images
        first_image = image_locations[0]
        if "/" in first_image:
            self.wdir = first_image[:first_image.rfind("/")+1]
        
        # create series data file (.ser)
        series_data = {}
        series_data["sections"] = []
        series_data["current_section"] = 0
        series_data["window"] = [0, 0, 1, 1]
        for i in range(len(image_locations)):
            series_data["sections"].append(series_name + "." + str(i))

        series_data["palette_traces"] = []

        diamond_trace = Trace("diamond", (255, 0, 0))
        diamond_trace.points = [(0, 0.5), (-0.5, 0), (0, -0.5), (0.5, 0)]
        series_data["palette_traces"].append(diamond_trace.getDict())

        triangle_trace = Trace("triangle", (0, 255, 0))
        triangle_trace.points = [(-0.5, -0.5), (0.5, -0.5), (0, 0.5)]
        series_data["palette_traces"].append(triangle_trace.getDict())

        circle_trace = Trace("circle", (0, 0, 255))
        circle_trace.points = [(-0.5, 0.16667), (-0.5, -0.16667), (-0.16667, -0.5), (0.16667, -0.5),
                               (0.5, -0.16667), (0.5, 0.16667), (0.16667, 0.5), (-0.16667, 0.5)]
        series_data["palette_traces"].append(circle_trace.getDict())

        square_trace = Trace("square", (255, 0, 255))
        square_trace.points = [(0.5, 0.5), (0.5, -0.5), (-0.5, -0.5), (-0.5, 0.5)]
        series_data["palette_traces"].append(square_trace.getDict())

        cross_trace = Trace("cross", (0, 255, 255))
        cross_trace.points = [(-0.5, 0.16667), (-0.5, -0.16667), (-0.16667, -0.16667),
                              (-0.16667, -0.5), (0.16667, -0.5), (0.16667, -0.16667),
                              (0.5, -0.16667), (0.5, 0.16667), (0.16667, 0.16667),
                              (0.16667, 0.5), (-0.16667, 0.5), (-0.16667, 0.16667)]
        series_data["palette_traces"].append(cross_trace.getDict())

        series_data["current_trace"] = diamond_trace.getDict()

        with open(self.wdir + series_name + ".ser", "w") as series_file:
            series_file.write(json.dumps(series_data, indent=2))
        
        # create section files (.#)
        for i in range(len(image_locations)):
            section_data = {}
            section_data["src"] = image_locations[i][image_locations[i].rfind("/")+1:]
            section_data["mag"] = mag
            section_data["thickness"] = thickness
            section_data["tform"] = [1, 0, 0, 0, 1, 0]
            section_data["traces"] = []
            with open(self.wdir + series_name + "." + str(i), "w") as section_file:
                section_file.write(json.dumps(section_data, indent=2))
    
        # open series after creating
        self.openSeries(self.wdir + series_name + ".ser")
    
    def openSeries(self, series_fp=None):
        """Open an existing series"""
        if series_fp: # if series is provided (only the case if opening from new)
            self.series = Series(series_fp)
        else: 
            # get series file from user
            series_fp, extension = QFileDialog.getOpenFileName(self, "Select Series", filter="*.ser")
            if series_fp == "":
                return
            self.series = Series(series_fp)
        self.series_fp = series_fp

        # change working directory to series location
        if "/" in series_fp:
            self.wdir = series_fp[:series_fp.rfind("/")+1]
        
        # create trace field for given section on last known window
        self.initField()
    
    def initField(self):
        """Create the field for tracing"""
        # set the main window to be slightly less than the size of the monitor
        screen = QApplication.primaryScreen()
        screen_rect = screen.size()
        x = 50
        y = 80
        w = screen_rect.width() - 100
        h = screen_rect.height() - 160
        self.setGeometry(x, y, w, h)

        # create status bar (at bottom of window)
        self.statusbar = self.statusBar()

        # add to menu bar
        self.objectmenu = self.menubar.addMenu("Object")
        self.objectlist_act = self.objectmenu.addAction("Open object list")
        self.objectlist_act.triggered.connect(self.openObjectList)

        # create the field and set as main widget
        self.section = Section(self.wdir + self.series.sections[self.series.current_section])
        self.field = FieldWidget(self.series.current_section, self.section, self.series.window, self)
        self.setCentralWidget(self.field)

        # create mouse dock
        self.mouse_dock = MouseDockWidget(self.series.palette_traces, self.series.current_trace, self)
        self.changeTracingTrace(self.series.current_trace) # set the current trace

        # create shortcuts
        save_sc = QShortcut(QKeySequence("Ctrl+S"), self)
        save_sc.activated.connect(self.saveAllData)
        merge_sc = QShortcut(QKeySequence("Ctrl+M"), self)
        merge_sc.activated.connect(self.field.mergeSelectedTraces)
        deselect_sc = QShortcut(QKeySequence("Ctrl+D"), self)
        deselect_sc.activated.connect(self.field.deselectAllTraces)
        hide_sc = QShortcut(QKeySequence("Ctrl+H"), self)
        hide_sc.activated.connect(self.field.hideSelectedTraces)
        hideall_sc = QShortcut(QKeySequence("Shift+H"), self)
        hideall_sc.activated.connect(self.field.toggleHideAllTraces)
    
    def changeMouseMode(self, new_mode):
        self.field.setMouseMode(new_mode)

    def changeTracingTrace(self, trace):
        self.series.current_trace = trace
        self.field.setTracingTrace(trace)
    
    def keyPressEvent(self, event):
        # do not respond to keyboard if field is not created
        if not self.field:
            return
        # if PgUp is pressed
        elif event.key() == 16777238 and self.series.current_section < len(self.series.sections)-1:
            self.changeSection(self.series.current_section + 1)
        # if PgDn is pressed
        elif event.key() == 16777239 and self.series.current_section > 0:
            self.changeSection(self.series.current_section - 1)
        # if Del is pressed
        elif event.key() == 16777223:
            self.field.deleteSelectedTraces()
    
    def wheelEvent(self, event):
        # do not respond to mouse wheel if field is not created
        if not self.field:
            return
        # if scroll up
        elif event.angleDelta().y() > 0  and self.series.current_section < len(self.series.sections)-1:
            self.changeSection(self.series.current_section + 1)
        # if scroll down
        elif event.angleDelta().y() < 0 and self.series.current_section > 0:
            self.changeSection(self.series.current_section - 1)
    
    def changeSection(self, section_num):
        """Change the section of the field"""
        self.saveAllData()
        self.series.current_section = section_num
        self.section = Section(self.wdir + self.series.sections[self.series.current_section])
        self.field.loadSection(self.series.current_section, self.section)
    
    def saveAllData(self):
        self.section.traces = self.field.traces
        self.series.window = self.field.current_window
        self.series.palette_traces = []
        for button in self.mouse_dock.palette_buttons:
            self.series.palette_traces.append(button.trace)
            if button.isChecked():
                self.series.current_trace = button.trace
        self.section.save()
        self.series.save()
    
    def openObjectList(self):
        self.saveAllData()
        quantities = {}
        quantities["range"] = True
        quantities["count"] = True
        quantities["surface_area"] = True
        quantities["flat_area"] = True
        quantities["volume"] = True
        obj_table = ObjectTableWidget(self.series, self.wdir, quantities, self)

    def closeEvent(self, event):
        """Save traces, section num, and window if user exits"""
        if not self.field: # do not do anything if field is not created
            event.accept()
            return
        self.saveAllData()
        event.accept()