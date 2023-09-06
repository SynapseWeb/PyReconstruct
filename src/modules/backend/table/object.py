from PySide6.QtCore import Qt

from modules.gui.table import ObjectTableWidget
from modules.datatypes import (
    Series,
    Section,
    Trace
)

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
    
    def newTable(self):
        """Create a new object list widget."""
        new_table = ObjectTableWidget(
            self.series,
            self.mainwindow,
            self
        )
        self.tables.append(new_table)
        self.mainwindow.addDockWidget(Qt.LeftDockWidgetArea, new_table)
    
    def updateSection(self, section : Section):
        """Update the data and the table for a specific section.
        
            Params:
                section (Section): the section object
                section_num (int): the section number
        """
        
        # refresh any removed traces
        updated_contours = section.getAllModifiedNames()
        self.updateObjects(updated_contours)

    # MENU FUNCTIONS

    def refresh(self):
        """Reload all of the section data."""
        self.mainwindow.saveAllData()
        self.series.data.refresh()
        for table in self.tables:
            table.createTable()
    
    def updateTable(self, table : ObjectTableWidget):
        """Updates a table with the current data.
        
            Params:
                table (ObjectTableWidget): the table to update
        """
        table.createTable()
    
    def updateObjects(self, obj_names : list):
        """Update the objects each table.
        
            Params:
                obj_names (list): the list objects to update
        """
        for table in self.tables:
            table.updateObjects(obj_names)
    
    def findObject(self, obj_name : str, first=True):
        """Find an object in the series.
        
            Params:
                obj_name (str): the name of the object
                first (bool): whether to find first or last object in series
        """
        self.mainwindow.saveAllData()
        if first:
            snum = self.series.data.getStart(obj_name)
        else:
            snum = self.series.data.getEnd(obj_name)
        self.mainwindow.setToObject(obj_name, snum)

    def deleteObjects(self, obj_names : list):
        """Delete an object or objects on every section.
        
            Params:
                obj_names (list): the list of names for the objects to delete
        """
        self.mainwindow.saveAllData()
        # delete the object on every section
        self.series.deleteObjects(obj_names)

        # update the dictionary data and tables
        self.updateObjects(obj_names)
        
        # update the view
        self.mainwindow.field.reload()
        self.mainwindow.seriesModified(True)

    def editAttributes(self, obj_names : list, attr_trace : Trace):
        """Edit objects on every section.
        
            Params:
                series (Series): the series object
                obj_names (list): the names of the objects to rename
                attr_trace (Trace): the trace holding the new attributes
        """
        self.mainwindow.saveAllData()
        
        # modify the object on every section
        t = attr_trace
        name, color, tags, mode = (
            t.name, t.color, t.tags, t.fill_mode
        )
        self.series.editObjectAttributes(
            obj_names,
            name,
            color,
            tags,
            mode
        )

        all_names = set(obj_names + [name])

        # update the table data
        self.updateObjects(all_names)
        
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
        
        # iterate through all sections
        self.series.editObjectRadius(
            obj_names,
            new_rad
        )
        
        # update the table data
        self.updateObjects(obj_names)
        
        # update the view
        self.mainwindow.field.reload()
        self.mainwindow.seriesModified(True)
    
    def editShape(self, obj_names : list, new_shape : list):
        """Change the shapes of all traces of an object.
        
            Params:
                obj_names (list): the names of objects to modify
                new_shape (list): the new shape for the traces of the object
        """
        self.mainwindow.saveAllData()
        
        # iterate through all sections
        self.series.editObjectShape(
            obj_names,
            new_shape
        )
        
        # update the table data
        self.updateObjects(obj_names)
        
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
        self.series.removeAllTraceTags(obj_names)

        self.updateObjects(obj_names)

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
        self.series.hideObjects(obj_names, hide)
            
        # update the view
        self.mainwindow.field.reload()
        self.mainwindow.seriesModified(True)
    
    def edit3D(self, obj_names : list, new_type : str, new_opacity : float):
        """Modify the 3D settings for a set of objects.
        
            Params:
                obj_names (list): the objects to modify
                new_type (str): the 3D type for the objects
                new_opacity (float): the opacity for the 3D objects
        """
        self.mainwindow.saveAllData()

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
    
    def createZtrace(self, obj_names : list, cross_sectioned : bool):
        """Create ztraces from a set of objects.
        
            Params:
                obj_names (list): the objects to create ztraces for
                croess_sectioned (bool): True if object is cross-sectioned
        """
        self.mainwindow.saveAllData()

        for name in obj_names:
            self.series.createZtrace(name, cross_sectioned)

        # update the ztrace table if one exists
        if self.mainwindow.field.ztrace_table_manager:
            self.mainwindow.field.ztrace_table_manager.refresh()
        
        self.mainwindow.seriesModified(True)
        self.mainwindow.field.reload()
    
    def close(self):
        """Close all tables."""
        for table in self.tables:
            table.close()


