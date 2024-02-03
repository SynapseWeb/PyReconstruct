from PySide6.QtCore import Qt

from PyReconstruct.modules.gui.table import TraceTableWidget
from PyReconstruct.modules.datatypes import (
    Series,
    Section
)

import sys

class TraceTableManager():

    def __init__(self, series : Series, section : Section, mainwindow):
        """Create the trace table manager.
        
            Params:
                series (Series): the series object
                section (Section): the section object
                mainwindow (MainWindow): the main window widget
        """
        self.tables = []
        self.series = series
        self.section = section
        self.mainwindow = mainwindow
        self.loadSection()

    def loadSection(self, section : Section = None):
        """Load all of the data for each object in the series.
        
            Params:
                section (Section): the section to load data for
        """
        if section:
            self.section = section
        # add the data to the tables
        for table in self.tables:
            table.createTable(self.section)
    
    def update(self):
        """Update the table for a section."""
        for table in self.tables:
            table.setContours(self.section.getAllModifiedNames())
    
    def newTable(self):
        """Create a new trace list."""
        new_table = TraceTableWidget(
            self.series,
            self.section,
            self.mainwindow,
            self
        )
        self.tables.append(new_table)
        self.mainwindow.addDockWidget(Qt.LeftDockWidgetArea, new_table)

    # MENU-RELATED FUNCTIONS
    
    def updateTable(self, table : TraceTableWidget):
        """Updates a table with the current data.
        
            Params:
                table (ObjectTableWidget): the table to update
        """
        table.createTable(self.section)
    
    def getTraces(self, items : list) -> list:
        """Get the trace objects for a list of table items.
        
            Params:
                items (list): the list of trace table items (name, index)
            Returns:
                traces (list): the list of actual trace objects
        """
        traces = []
        for name, index in items:
            traces.append(self.section.contours[name][index])
        
        return traces
    
    def editTraces(self, traces : list, name : str, color : tuple, tags : set, mode : tuple):
        """Edit a set of traces.
        
            Params:
                traces (list): the list of traces to modify
                name (str): the new trace name
                color (tuple): the new trace color
                tags (set): the new trace tags
                mode (tuple): the fill mode for the traces
        """
        self.mainwindow.field.section.editTraceAttributes(traces, name, color, tags, mode)
        self.mainwindow.field.generateView(generate_image=False)
        self.mainwindow.field.saveState()
    
    def hideTraces(self, traces, hide=True):
        """Hide/unhide a set of traces.
        
            Params:
                traces (list): the list of traces to hide/unhide
                hide (bool): True if traces should be hidden
        """
        self.mainwindow.field.section.hideTraces(traces, hide)
        self.mainwindow.field.generateView()
        self.mainwindow.field.saveState()
    
    def closeTraces(self, traces, closed=True):
        """Hide/unhide a set of traces.
        
            Params:
                traces (list): the list of traces to modify
                closed (bool): True if traces should be closed
        """
        self.mainwindow.field.section.closeTraces(traces, closed)
        self.mainwindow.field.generateView()
        self.mainwindow.field.saveState()
    
    def editRadius(self, traces : list, new_rad : float):
        """Edit the radius of a set of traces
        
            Params:
                traces (list): the list of traces to modify
                new_rad (float): the new radius for the traces
        """
        self.mainwindow.field.section.editTraceRadius(traces, new_rad)
        self.mainwindow.field.generateView(generate_image=False)
        self.mainwindow.field.saveState()
    
    def editShape(self, traces : list, new_shape : float):
        """Edit the shape of a set of traces
        
            Params:
                traces (list): the list of traces to modify
                new_rad (float): the new shape for the traces
        """
        self.mainwindow.field.section.editTraceShape(traces, new_shape)
        self.mainwindow.field.generateView(generate_image=False)
        self.mainwindow.field.saveState()
    
    def findTrace(self, item):
        """Find an object in the series.
        
            Params:
                item (tuple): the iname, index of the desired trace
        """
        name, index = item
        self.mainwindow.field.findTrace(name, index)
    
    def deleteTraces(self, traces : list):
        """Delete a set of traces.
        
            Params:
                traces (list): the trace to delete
        """
        self.mainwindow.field.deleteTraces(traces)
        
    def close(self):
        """Close all tables."""
        for table in self.tables:
            table.close()


