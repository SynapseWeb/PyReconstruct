from PySide6.QtCore import Qt

from modules.gui.object_table_widget import ObjectTableWidget
from modules.gui.object_3D_viewer import Object3DViewer
from modules.gui.history_widget import HistoryWidget

from modules.pyrecon.series import Series
from modules.pyrecon.section import Section
from modules.pyrecon.trace import Trace

from modules.backend.object_table_item import ObjectTableItem
from modules.backend.gui_functions import progbar

class ObjectTableManager():

    def __init__(self, series : Series, mainwindow):
        self.tables = []
        self.series = series
        self.mainwindow = mainwindow

        self.object_viewer = None
        self.opacity = 255
        self.sc_size = 1

        self.loadSeriesData()

    def loadSeriesData(self):
        """Load all of the data for each object in the series."""
        # create the progress bar
        update, canceled = progbar("Load Series", "Loading series...")

        self.objdict = {}  # object name : ObjectTableItem (contains data on object)
        prog_value = 0
        final_value = len(self.series.sections)
        # iterate through sections, keep track of progress
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
            prog_value += 1
            update(prog_value / final_value * 100)
            if canceled(): return
    
    def newTable(self):
        """Create a new object list."""
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
        """Refresh an object's data on the table.
        
            Params:
                (obj_name): the name of the object to refresh
        """
        for table in self.tables:
            table.updateObject(self.objdict[obj_name])

    # MENU FUNCTIONS

    def refresh(self):
        """Reload all of the section data."""
        self.loadSeriesData()
        for table in self.tables:
            table.createTable(self.objdict)
    
    def updateTable(self, table : ObjectTableWidget):
        """Updates a table with the current data.
        
            Params:
                table (ObjectTableWidget): the table to update
        """
        table.createTable(self.objdict)
    
    def findObject(self, obj_name, first=True):
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
        """Delete an object on every section.
        
            Params:
                series (Series): the series object
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

    def modifyObjects(self, obj_names : list, name : str = None, color : tuple = None):
        """Rename objects on every section.
        
            Params:
                series (Series): the series object
                obj_names (list): the names of the objects to rename
                name (str): the new name for the objects
                color (tuple): the new color for the objects
        """
        self.mainwindow.saveAllData()
        # modify the object on every section
        for snum in self.series.sections:
            section = self.series.loadSection(snum)
            for obj_name in obj_names:
                if obj_name in section.contours:
                    contour = section.contours[obj_name]
                    for trace in contour:
                        if name:
                            trace.name = name
                        if color:
                            trace.color = color
                    if name:
                        contour.name = name
                        # check if the new name exists in the section
                        if name in section.contours:
                            section.contours[name] += contour
                        else:
                            section.contours[name] = contour
                        del(section.contours[obj_name])
                    section.save()
        
        # update the dictionary data
        if name:
            for obj_name in obj_names:
                if name in self.objdict:
                    self.objdict[name].combine(self.objdict[obj_name])
                else:
                    self.objdict[name] = self.objdict[obj_name].copy(name)
                self.objdict[obj_name].clearAllData()

        # update the table data
        for table in self.tables:
            for obj_name in obj_names:
                table.updateObject(self.objdict[obj_name])
            if name:
                table.updateObject(self.objdict[name])
        
        # update the view
        self.mainwindow.field.reload()
    
    def hideObjects(self, obj_names, hide=True):
        """Hide all traces of an object throughout the series."""
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

    def editRadius(self, obj_names, new_rad):
        """Change the radii of all traces of an object."""
        self.mainwindow.saveAllData()
        # delete existing trace information
        for name in obj_names:
            self.objdict[name] = ObjectTableItem(name)
        
        # iterate through all sections
        for snum in self.series.sections:
            section = self.series.loadSection(snum)
            modified = False
            for name in obj_names:
                if name in section.contours:
                    contour = section.contours[name]
                    for trace in contour:
                        # modify the trace
                        trace.resize(new_rad)
                        modified = True
                        # add trace data
                        self.addTrace(trace, section, snum)
            if modified:
                section.save()
        
        # update the table data
        for table in self.tables:
            for name in obj_names:
                table.updateObject(self.objdict[name])
        
        # update the view
        self.mainwindow.field.reload()
    
    def tagTraces(self, obj_names : list, tag_name : str, remove=False):
        """Tag all the traces on a set of objects.
        
            Params:
                obj_names (list): a list of object names
                tag_name (str): the name of the tag to add
        """
        self.mainwindow.saveAllData()
        for snum in self.series.sections:
            section = self.series.loadSection(snum)
            section_modified = False
            for name in obj_names:
                if name in section.contours:
                    for trace in section.contours[name]:
                        if not remove:
                            trace.tags.add(tag_name)
                            self.objdict[trace.name].addTag(tag_name, snum)
                            section_modified = True
                        else:
                            if tag_name in trace.tags:
                                trace.tags.remove(tag_name)
                                self.objdict[trace.name].removeTag(tag_name, snum)
                                section_modified = True
            if section_modified:
                section.save()
        
        for table in self.tables:
            for name in obj_names:
                table.updateObject(self.objdict[name])
    
    def removeAllTraceTags(self, obj_names : list):
        """Remove all tags from all trace on a selected object.
        
            Params:
                obj_names (list): a list of object names
        """
        self.mainwindow.saveAllData()
        for snum in self.series.sections:
            section = self.series.loadSection(snum)
            section_modified = False
            for name in obj_names:
                if name in section.contours:
                    for trace in section.contours[name]:
                        trace.tags = set()
                        section_modified = True
            if section_modified:
                section.save()
        for name in obj_names:
            self.objdict[trace.name].clearTags()

        for table in self.tables:
            for name in obj_names:
                table.updateObject(self.objdict[name])
    
    def setOpacity(self, opacity):
        self.opacity = opacity
    
    def setSCSize(self, size):
        self.sc_size = size
    
    def generate3D(self, obj_names):
        """Generate the 3D view for a list of objects.
        
            Params:
                obj_names (list): a list of object names
        """
        if self.object_viewer:
            self.object_viewer.close()
        self.object_viewer = Object3DViewer(
            self.series,
            obj_names,
            self.opacity,
            self.sc_size,
            self.mainwindow
    )
    
    def viewHistory(self, obj_names):
        """View the log history of a set of objects."""
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
        
        log_history.sort()

        output_str = "Object history for: " + ", ".join(sorted(obj_names)) + "\n"
        for log, name, snum in log_history:
            output_str += f"Section {snum} "
            output_str += name + " "
            output_str += str(log) + "\n"
        
        HistoryWidget(self.mainwindow, output_str)
    
    def createZtrace(self, obj_names):
        """Create ztraces from a set of objects."""
        for name in obj_names:
            self.series.createZtrace(name)
    
    def close(self):
        """Close all tables."""
        for table in self.tables:
            table.close()


