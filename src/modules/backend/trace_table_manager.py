from PySide6.QtCore import Qt

from modules.gui.trace_table_widget import TraceTableWidget
from modules.gui.history_widget import HistoryWidget

from modules.pyrecon.series import Series
from modules.pyrecon.section import Section

from modules.backend.trace_table_item import TraceTableItem

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
        self.data = {}
        for c in self.section.contours:
            self.data[c] = []
            index = 0
            for trace in self.section.contours[c]:
                self.data[c].append(
                    TraceTableItem(
                        trace,
                        self.section.tforms[self.series.alignment],
                        index
                    )
                )
                index += 1
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
                self.section.tforms[self.series.alignment],
                len(contour)
            )
            contour.append(item)
            for table in self.tables:
                table.addItem(item)
        # update removed traces
        for trace in self.section.removed_traces:
            contour = self.data[trace.name]
            for index, item in enumerate(contour):
                if item.isTrace(trace):
                    contour.remove(item)
                    break
            for i in range(index, len(contour)):
                contour[i].index -= 1
            for table in self.tables:
                table.removeItem(item)
    
    def newTable(self):
        """Create a new trace list."""
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
    
    def editTraces(self, name : str, color : tuple, tags : set, traces : list):
        """Edit a set of traces.
        
            Params:
                name (str): the new trace name
                color (tuple): the new trace color
                tags (set): the new trace tags
                traces (list): the list of traces to modify
        """
        self.mainwindow.field.section_layer.changeTraceAttributes(name, color, tags, traces)
        self.mainwindow.field.saveState()
        self.mainwindow.field.generateView(generate_image=False)
    
    def hideTraces(self, traces, hide=True):
        """Hide/unhide a set of traces.
        
            Params:
                traces (list): the list of traces to hide/unhide
                hide (bool): True if traces should be hidden
        """
        self.mainwindow.field.hideTraces(traces, hide)
    
    def editRadius(self, new_rad : float, traces : list):
        """Edit the radius of a set of traces
        
            Params:
                new_rad (float): the new radius for the traces
                traces (list): the list of traces to modify
        """
        self.mainwindow.field.editRadius(new_rad, traces)
    
    def findTrace(self, item : TraceTableItem):
        """Find an object in the series.
        
            Params:
                item (TraceTableItem): the item corresponding to the desired trace
        """
        self.mainwindow.field.findTrace(item.name, item.index)
    
    def deleteTraces(self, traces : list):
        """Delete a set of traces.
        
            Params:
                traces (list): the trace to delete
        """
        self.mainwindow.field.deleteTraces(traces)
    
    def viewHistory(self, traces : list):
        """View the log history of a set of traces.
        
            Params:
                traces (list): the traces to view the history of
        """
        log_history = []
        names = set()
        for trace in traces:
            names.add(trace.name)
            for log in trace.history:
                log_history.append((log, trace.name))
        log_history.sort()
        
        # get the trace names
        names = sorted(list(names))
        output_str = "Trace history for: " + ", ".join(names) + "\n"
        for log, name in log_history:
            output_str += name + " "
            output_str += str(log) + "\n"
        
        HistoryWidget(self.mainwindow, output_str)
        
    def close(self):
        """Close all tables."""
        for table in self.tables:
            table.close()


