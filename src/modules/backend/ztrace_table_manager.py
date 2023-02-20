from PySide6.QtCore import Qt

from modules.pyrecon.series import Series

from modules.backend.ztrace_table_item import ZtraceTableItem

from modules.gui.ztrace_table_widget import ZtraceTableWidget

class ZtraceTableManager():

    def __init__(self, series : Series, mainwindow):
        """Create the ztrace table manager.
        
            Params:
                series (Series): the series object
                mainwindow (MainWindow): the main window widget"""
        self.tables = []
        self.series = series
        self.mainwindow = mainwindow
        self.loadSeries()
    
    def loadSeries(self):
        """Load the secion thicknesses and transforms from the series."""
        # load the transforms and section heights
        self.tforms = {}
        self.section_heights = {}
        height = 0
        for snum in sorted(self.series.sections.keys()):
            section = self.series.loadSection(snum)
            tform = section.tforms[self.series.alignment]
            self.tforms[snum] = tform
            self.section_heights[snum] = height
            height += section.thickness
        
        # load the ztrace data
        self.data = {}
        for ztrace in self.series.ztraces:
            self.data[ztrace.name] = ZtraceTableItem(
                ztrace,
                self.tforms,
                self.section_heights
            )
    
    def refresh(self):
        """Refresh the series data."""
        self.loadSeries()
        for table in self.tables:
            table.createTable(self.data)
    
    def newTable(self):
        """Create a new ztrace list."""
        new_table = ZtraceTableWidget(
            self.series,
            self.data,
            self.mainwindow,
            self
        )
        self.tables.append(new_table)
        self.mainwindow.addDockWidget(Qt.LeftDockWidgetArea, new_table)
    
    def updateTable(self, table : ZtraceTableWidget):
        """Update a table's data.
        
            Params:
                table: the table to update
        """
        table.createTable(self.data)
    
    # MENU-REALTED FUNCTIONS

    def editName(self, name : str, new_name : str):
        """Edit the name of a ztrace.
        
            Params:
                name (str): the name of the ztrace to change
                new_name (str): the new name for the trace
        """
        # modify the ztrace data
        for ztrace in self.series.ztraces:
            if ztrace.name == name:
                ztrace.name = new_name
                break
        
        # modify the tables
        self.data[new_name] = self.data[name]
        self.data[new_name].name = new_name
        del(self.data[name])
        for table in self.tables:
            table.createTable(self.data)
    
    def smooth(self, names : list):
        """Smooth a set of ztraces.
        
            Params:
                names (list): the names of the ztraces to smooth
        """
        # smooth the ztraces
        for ztrace in self.series.ztraces:
            if ztrace.name in names:
                ztrace.smooth()
                # update the table data
                self.data[ztrace.name] = ZtraceTableItem(
                    ztrace,
                    self.tforms,
                    self.section_heights
                )
        
        for table in self.tables:
            table.createTable(self.data)
        
    def addTo3D(self, names : list):
        """Add a set of ztraces to the 3D scene."""
        # access the object viewer object
        obj_table_manager = self.mainwindow.field.obj_table_manager
        if not obj_table_manager:
            return
        object_viewer = obj_table_manager.object_viewer
        if not object_viewer:
            return
        
        object_viewer.addZtraces(names)

    def delete(self, names : list):
        """Delete a set of ztraces.
        
            Params:
                names (list): the list of ztraces to delete
        """
        for ztrace in self.series.ztraces:
            if ztrace.name in names:
                self.series.ztraces.remove(ztrace)
                del(self.data[ztrace.name])
        
        for table in self.tables:
            table.createTable(self.data)
    
    def close(self):
        """Close all the tables."""
        for table in self.tables:
            table.close()
        

        
        
            

