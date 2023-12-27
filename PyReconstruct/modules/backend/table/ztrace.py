from PySide6.QtCore import Qt

from PyReconstruct.modules.datatypes import (
    Series
)
from PyReconstruct.modules.gui.table import ZtraceTableWidget

class ZtraceTableManager():

    def __init__(self, series : Series, mainwindow):
        """Create the ztrace table manager.
        
            Params:
                series (Series): the series object
                mainwindow (MainWindow): the main window widget"""
        self.tables = []
        self.series = series
        self.mainwindow = mainwindow
        self.series_states = self.mainwindow.field.series_states
    
    def refresh(self):
        """Refresh the series data."""
        self.mainwindow.field.refreshTables(refresh_data=True)
    
    def newTable(self):
        """Create a new ztrace list."""
        new_table = ZtraceTableWidget(
            self.series,
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
        table.createTable()
    
    def updateTables(self):
        """Update all the ztrace tables."""
        for table in self.tables:
            table.createTable()
    
    def update(self, clear_tracking=False):
        """Update the data for a set of ztraces."""
        for table in self.tables:
            table.updateZtraces(self.series.modified_ztraces)
        if clear_tracking:
            self.series.modified_ztraces = set()

    # MENU-REALTED FUNCTIONS

    def editAttributes(self, name : str, new_name : str, new_color : tuple, log_event=True):
        """Edit the name of a ztrace.
        
            Params:
                name (str): the name of the ztrace to change
                new_name (str): the new name for the trace
                new_color (tuple): the new color for the trace
        """
        # save the series state
        self.series_states.addState()

        # modify the ztrace data
        ztrace = self.series.ztraces[name]
        if new_name:
            ztrace.name = new_name
            if new_name != name:  # if renamed
                del(self.series.ztraces[name])
                self.series.ztraces[new_name] = ztrace
                # update group data
                groups = self.series.ztrace_groups.getObjectGroups(name)
                for g in groups:
                    self.series.ztrace_groups.add(g, new_name)
                self.series.ztrace_groups.removeObject(name)
        if new_color:
            ztrace.color = new_color
        
        if log_event:
            if new_name != name:
                self.series.addLog(name, None, f"Rename ztrace to {new_name}")
                self.series.addLog(new_name, None, f"Create ztrace from {name}")
            else:
                self.series.addLog(name, None, "Modify ztrace")
        
        # modify the tables
        if new_name and new_name != name:
            self.series.modified_ztraces.add(new_name)
            self.series.modified_ztraces.add(name)
            self.update(clear_tracking=True)
        
        # update the view
        self.mainwindow.field.reload()
        self.mainwindow.seriesModified(True)
    
    def smooth(self, names : list, smooth : int, newztrace : bool, log_event=True):
        """Smooth a set of ztraces.
        
            Params:
                names (list): the names of the ztraces to smooth
                smooth (int): the smoothing factor
                newztrace (bool): False if ztrace should be overwritten
        """
        # save the series state
        self.series_states.addState()
        
        # smooth the ztraces
        for name in names:
            # create a new ztrace if requested
            if newztrace:
                ztrace = self.series.ztraces[name].copy()
                new_name = f"{ztrace.name}_smooth{smooth}"
                ztrace.name = new_name
                self.series.ztraces[new_name] = ztrace
            else:
                ztrace = self.series.ztraces[name]
            ztrace.smooth(self.series, smooth)
            self.series.modified_ztraces.add(ztrace.name)
        
            if log_event:
                self.series.addLog(name, None, "Smooth ztrace")
        
        self.update(clear_tracking=True)
        
        # update the view
        self.mainwindow.field.reload()
        self.mainwindow.seriesModified(True)

    def delete(self, names : list, log_event=True):
        """Delete a set of ztraces.
        
            Params:
                names (list): the list of ztraces to delete
        """
        # save the series state
        self.series_states.addState()
        
        for name in names:
            del(self.series.ztraces[name])
            self.series.modified_ztraces.add(name)
            # update the group data
            self.series.ztrace_groups.removeObject(name)
        
        self.update(clear_tracking=True)
        self.series.modified_ztraces = set()

        if log_event:
            self.series.addLog(name, None, "Delete ztrace")

        # update the view
        self.mainwindow.field.reload()
        self.mainwindow.seriesModified(True)
    
    def close(self):
        """Close all the tables."""
        for table in self.tables:
            table.close()
        

        
        
            

