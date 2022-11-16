from PySide6.QtCore import Qt

from modules.gui.trace_table_widget import TraceTableWidget

from modules.pyrecon.series import Series
from modules.pyrecon.section import Section

from modules.backend.trace_table_item import TraceTableItem

class TraceTableManager():

    def __init__(self, series : Series, section : Section, mainwindow):
        self.tables = []
        self.series = series
        self.section = section
        self.mainwindow = mainwindow
        self.loadSection()

    def loadSection(self, section : Section = None):
        """Load all of the data for each object in the series."""
        if section:
            self.section = section
        self.data = {}
        for c in self.section.contours:
            self.data[c] = []
            for trace in self.section.contours[c]:
                self.data[c].append(
                    TraceTableItem(
                        trace,
                        self.section.tforms[self.series.alignment]
                    )
                )
        # add the data to the tables
        for table in self.tables:
            table.createTable(self.data)
    
    def update(self):
        """Update the table for a section."""
        # update added traces
        for trace in self.section.added_traces:
            if trace.name in self.data:
                contour = self.data[trace.name]
            else:
                contour = []
                self.data[trace.name] = contour
            item = TraceTableItem(
                trace,
                self.section.tforms[self.series.alignment]
            )
            contour.append(item)
            for table in self.tables:
                table.addItem(item)
        # update removed traces
        for trace in self.section.removed_traces:
            contour = self.data[trace.name]
            for item in contour:
                if item.isTrace(trace):
                    self.data[trace.name].remove(item)
                    break
            for table in self.tables:
                table.removeItem(item)
    
    def newTable(self):
        """Create a new object list."""
        new_table = TraceTableWidget(
            self.series,
            self.data,
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
        table.createTable(self.data)
    
    def getTraces(self, items : list) -> list:
        """Get the trace objects for a list of table items.
        
            Params:
                items (list): the list of trace table items
            Returns:
                (list) the trace objects
        """
        # get the trace indeces in the contour list
        indeces = {}
        for item in items:
            if item.name not in indeces:
                indeces[item.name] = []
            indeces[item.name].append(self.data[item.name].index(item))
        # get the actual trace objects
        traces = []
        for name in indeces:
            for i in indeces[name]:
                traces.append(self.section.contours[name][i])
        
        return traces
    
    def editTraces(self, name, color, tags, traces):
        self.mainwindow.field.section_layer.changeTraceAttributes(name, color, tags, traces)
        self.mainwindow.field.saveState()
        self.mainwindow.field.generateView(generate_image=False)
    
    def editRadius(self, new_rad, traces):
        self.mainwindow.field.section_layer.changeTraceRadius(new_rad, traces)
        self.mainwindow.field.saveState()
        self.mainwindow.field.generateView(generate_image=False)
    
    def findTrace(self, item : TraceTableItem):
        """Find an object in the series.
        
            Params:
                item (TraceTableItem): the item corresponding to the desired trace
        """
        index = self.data[item.name].index(item)
        self.mainwindow.field.findTrace(item.name, index)
    
    def deleteTraces(self, traces):
        self.mainwindow.field.section_layer.deleteSelectedTraces(traces)
        self.mainwindow.field.saveState()
        self.mainwindow.field.generateView(generate_image=False)
    
    def close(self):
        """Close all tables."""
        for table in self.tables:
            table.close()


