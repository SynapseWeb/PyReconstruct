from PySide6.QtCore import Qt

from modules.gui.object_table_widget import ObjectTableWidget
from modules.gui.object_3D_viewer import Object3DViewer
from modules.gui.history_widget import HistoryWidget

from modules.pyrecon.series import Series
from modules.pyrecon.section import Section
from modules.pyrecon.trace import Trace

from modules.backend.object_table_item import ObjectTableItem
from modules.gui.gui_functions import progbar

class ObjectTableManager():

    def __init__(self, series : Series, mainwindow):
        """Create the object table manager.
        
            Params:
                series (Series): the series object
                mainwindow (MainWindow): the parent main window object
        """
        self.tables = []
        self.series = series
        self.mainwindow = mainwindow

        self.object_viewer = None

        self.loadSeriesData()

    def loadSeriesData(self):
        """Load all of the data for each object in the series."""
        # create the progress bar
        update, canceled = progbar("Load Series", "Loading series...")

        self.objdict = {}  # object name : ObjectTableItem (contains data on object)
        prog_value = 0
        final_value = len(self.series.sections)

        for section_num in self.series.sections:
            section = self.series.loadSection(section_num)
            # iterate through contours
            for contour_name in section.contours:
                if contour_name not in self.objdict:
                    self.objdict[contour_name] = ObjectTableItem(contour_name)
                # iterate through traces
                for trace in section.contours[contour_name]:
                    # add to existing data
                    self.objdict[contour_name].addTrace(
                        trace,
                        section.tforms[self.series.alignment],
                        section_num,
                        section.thickness
                    )
                
            # update progress bar
            prog_value += 1
            update(prog_value / final_value * 100)
            if canceled(): return
    
    def newTable(self):
        """Create a new object list widget."""
        new_table = ObjectTableWidget(
            self.series,
            self.objdict,
            self.mainwindow,
            self
        )
        self.tables.append(new_table)
        self.mainwindow.addDockWidget(Qt.LeftDockWidgetArea, new_table)
    
    def updateSection(self, section : Section, section_num : int):
        """Update the data and the table for a specific section.
        
            Params:
                section (Section): the section object
                section_num (int): the section number
        """
        # add and update and added traces
        for trace in section.added_traces:
            self.addTrace(trace, section, section_num)
        
        # refresh any removed traces
        updated_contours = set()
        for trace in section.removed_traces:
            if trace.name not in updated_contours:
                self.updateContour(trace.name, section, section_num)
                updated_contours.add(trace.name)
    
    def addTrace(self, trace : Trace, section : Section, section_num : int):
        """Add a trace to the existing object data and update the table.
        
            Params:
                trace (Trace): the trace to add
                section (Section): the section containing the trace
                section_num (int): the section number
        """
        # get the table item object
        if trace.name in self.objdict:
            objdata = self.objdict[trace.name]
        else:
            objdata = ObjectTableItem(trace.name)
            self.objdict[trace.name] = objdata
        
        # add trace data
        objdata.addTrace(
            trace,
            section.tforms[self.series.alignment],
            section_num,
            section.thickness
        )
    
        # update on the tables
        for table in self.tables:
            table.updateObject(objdata)

    def updateContour(self, contour_name : str, section : Section, section_num : int):
        """Update data and table for a specific contour.
        
            Params:
                contour_name (str): the name of the contour to update
                section (Section): the section object containing this contour
                section_num (int): the section number for this contour
        """
        # locate the object in the dictionary and clear existing section data
        if contour_name in self.objdict:
            objdata = self.objdict[contour_name]
            objdata.clearSectionData(section_num)
        else:
            objdata = ObjectTableItem(contour_name)
            self.objdict[contour_name] = objdata
        
        # update the trace in the dictionary if exists
        if contour_name in section.contours:
            for trace in section.contours[contour_name]:
                objdata.addTrace(
                    trace,
                    section.tforms[self.series.alignment],
                    section_num,
                    section.thickness
                )
        
        # update the contour on the table(s)
        for table in self.tables:
            table.updateObject(objdata)
    
    def refreshObject(self, obj_name : str):
        """Refresh an object's data on the tables.
        
            Params:
                (obj_name): the name of the object to refresh
        """
        for table in self.tables:
            table.updateObject(self.objdict[obj_name])

    # MENU FUNCTIONS

    def refresh(self):
        """Reload all of the section data."""
        self.mainwindow.saveAllData()
        self.loadSeriesData()
        for table in self.tables:
            table.createTable(self.objdict)
    
    def updateTable(self, table : ObjectTableWidget):
        """Updates a table with the current data.
        
            Params:
                table (ObjectTableWidget): the table to update
        """
        table.createTable(self.objdict)
    
    def findObject(self, obj_name : str, first=True):
        """Find an object in the series.
        
            Params:
                obj_name (str): the name of the object
                first (bool): whether to find first or last object in series
        """
        self.mainwindow.saveAllData()
        if first:
            snum = self.objdict[obj_name].getStart()
        else:
            snum = self.objdict[obj_name].getEnd()
        self.mainwindow.setToObject(obj_name, snum)

    def deleteObjects(self, obj_names : list):
        """Delete an object or objects on every section.
        
            Params:
                obj_names (list): the list of names for the objects to delete
        """
        self.mainwindow.saveAllData()
        for obj_name in obj_names:
            # delete the object on every section
            for snum in self.series.sections:
                section = self.series.loadSection(snum)
                if obj_name in section.contours:
                    del(section.contours[obj_name])
                    section.save()
            # update the dictionary data and tables
            self.objdict[obj_name].clearAllData()
            for table in self.tables:
                table.updateObject(self.objdict[obj_name])
        
        # update the view
        self.mainwindow.field.reload()
        self.mainwindow.seriesModified(True)

    def editAttributes(self, obj_names : list, name : str = None, color : tuple = None, tags : set = None, mode : tuple = None):
        """Rename objects on every section.
        
            Params:
                series (Series): the series object
                obj_names (list): the names of the objects to rename
                name (str): the new name for the objects
                color (tuple): the new color for the objects
        """
        self.mainwindow.saveAllData()
        # delete existing trace information
        for obj_name in obj_names:
            self.objdict[obj_name] = ObjectTableItem(obj_name)
        
        # modify the object on every section
        for snum in self.series.sections:
            section = self.series.loadSection(snum)
            traces = []
            for obj_name in obj_names:
                if obj_name in section.contours:
                    traces += section.contours[obj_name].getTraces()
            if traces:
                section.editTraceAttributes(traces, name, color, tags, mode, add_tags=True)
                # add trace data to table data
                for trace in traces:
                    self.addTrace(trace, section, snum)
                section.save()

        # update the table data
        for table in self.tables:
            for obj_name in obj_names:
                table.updateObject(self.objdict[obj_name])
            if name:
                table.updateObject(self.objdict[name])
        
        # update the view
        self.mainwindow.field.reload()
        self.mainwindow.seriesModified(True)      

    def editRadius(self, obj_names : list, new_rad : float):
        """Change the radii of all traces of an object.
        
            Params:
                obj_names (list): the names of objects to modify
                new_rad (float): the new radius for the traces of the object
        """
        self.mainwindow.saveAllData()
        # delete existing trace information
        for name in obj_names:
            self.objdict[name] = ObjectTableItem(name)
        
        # iterate through all sections
        for snum in self.series.sections:
            section = self.series.loadSection(snum)
            traces = []
            for name in obj_names:
                if name in section.contours:
                    traces += section.contours[name].getTraces()
            if traces:
                section.editTraceRadius(traces, new_rad)
                # add trace data to table data
                for trace in traces:
                    self.addTrace(trace, section, snum)
                section.save()
        
        # update the table data
        for table in self.tables:
            for name in obj_names:
                table.updateObject(self.objdict[name])
        
        # update the view
        self.mainwindow.field.reload()
        self.mainwindow.seriesModified(True)
    
    def removeAllTraceTags(self, obj_names : list):
        """Remove all tags from all trace on a selected object.
        
            Params:
                obj_names (list): a list of object names
        """
        self.mainwindow.saveAllData()

        # iterate through all the sections
        for snum in self.series.sections:
            section = self.series.loadSection(snum)
            traces = []
            for obj_name in obj_names:
                if obj_name in section.contours:
                    traces += section.contours[obj_name].getTraces()
            if traces:
                section.editTraceAttributes(
                    traces,
                    name=None,
                    color=None,
                    tags=set(),
                    mode=None, 
                )
                section.save()

        # modify the dictionary data
        for name in obj_names:
            self.objdict[name].clearTags()

        for table in self.tables:
            for name in obj_names:
                table.updateObject(self.objdict[name])

        # update the view
        self.mainwindow.field.reload()        
        self.mainwindow.seriesModified(True)

    def hideObjects(self, obj_names : list, hide=True):
        """Hide all traces of an object throughout the series.
        
            Params:
                obj_names (list): the names of objects to hide
                hide (bool): True if object should be hidden
        """
        self.mainwindow.saveAllData()
        # iterate through sections and hide the traces
        for snum in self.series.sections:
            modified = False
            section = self.series.loadSection(snum)
            for name in obj_names:
                if name in section.contours:
                    contour = section.contours[name]
                    for trace in contour:
                        trace.setHidden(hide)
                        modified = True
            if modified:
                section.save()
            
        # update the view
        self.mainwindow.field.reload()
        self.mainwindow.seriesModified(True)
    
    def generate3D(self, obj_names):
        """Generate the 3D view for a list of objects.
        
            Params:
                obj_names (list): a list of object names
        """
        if self.object_viewer and not self.object_viewer.closed:
            self.object_viewer.addObjects(obj_names)
        else:
            self.object_viewer = Object3DViewer(
                self.series,
                obj_names,
                self.mainwindow
            )
    
    def edit3D(self, obj_names : list, new_type : str, new_opacity : float):
        """Modify the 3D settings for a set of objects.
        
            Params:
                obj_names (list): the objects to modify
                new_type (str): the 3D type for the objects
                new_opacity (float): the opacity for the 3D objects
        """
        # set the series settings
        for name in obj_names:
            if name in self.series.object_3D_modes:
                obj_settings = list(self.series.object_3D_modes[name])
            else:
                obj_settings = ["surface", 1]
            if new_type:
                obj_settings[0] = new_type
            if new_opacity:
                obj_settings[1] = new_opacity
            self.series.object_3D_modes[name] = tuple(obj_settings)
        
        self.mainwindow.seriesModified(True)
    
    def viewHistory(self, obj_names : list):
        """View the log history of a set of objects.
        
            Params:
                obj_names (list): the objects to view the history of
        """
        self.mainwindow.saveAllData()

        # load all log objects from the traces
        log_history = []
        update, canceled = progbar("Object History", "Loading history...")
        progress = 0
        final_value = len(self.series.sections)
        for snum in self.series.sections:
            section = self.series.loadSection(snum)
            for name in obj_names:
                if name in section.contours:
                    contour = section.contours[name]
                    for trace in contour:
                        for log in trace.history:
                            log_history.append((log, name, snum))
            if canceled():
                return
            progress += 1
            update(progress/final_value * 100)
        
        # sort the log history by datetime
        log_history.sort()

        # create the output
        output_str = "Object history for: " + ", ".join(sorted(obj_names)) + "\n"
        for log, name, snum in log_history:
            output_str += f"Section {snum} "
            output_str += name + " "
            output_str += str(log) + "\n"
        
        HistoryWidget(self.mainwindow, output_str)
    
    def createZtrace(self, obj_names : list):
        """Create ztraces from a set of objects.
        
            Params:
                obj_names (list): the objects to create ztraces for
        """
        for name in obj_names:
            self.series.createZtrace(name)
        
        self.mainwindow.seriesModified(True)
    
    def close(self):
        """Close all tables."""
        for table in self.tables:
            table.close()


