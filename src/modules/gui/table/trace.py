import re
import os

from PySide6.QtWidgets import (
    QMainWindow, 
    QDockWidget, 
    QTableWidgetItem, 
    QAbstractItemView, 
    QWidget, 
    QInputDialog, 
    QMenu, 
    QFileDialog
)
from PySide6.QtCore import Qt

from .copy_table_widget import CopyTableWidget

from modules.datatypes import (
    Series,
    Section,
    TraceData
)
from modules.gui.utils import populateMenuBar, populateMenu
from modules.gui.dialog import TableColumnsDialog, TraceDialog
from modules.constants import fd_dir

class TraceTableWidget(QDockWidget):

    def __init__(self, series : Series, section : Section, mainwindow : QWidget, manager):
        """Create the trace table dock widget.
        
            Params:
                series (Series): the series object
                contourdict (dict): contains all trace info for the table
                mainwindow (QWidget): the main window the dock is connected to
                manager: the trace table manager
        """
        # initialize the widget
        super().__init__(mainwindow)
        self.mainwindow = mainwindow
        self.series = series
        self.section = section

        # set desired format for widget
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)  # ccan be docked to right or left side
        self.setWindowTitle("Trace List")

        # set defaults
        self.columns = {
            "Index" : False,
            "Tags" : True,
            "Length" : True,
            "Area" : True,
            "Radius": True,
        }
        self.re_filters = set([".*"])
        self.tag_filters = set()
        self.group_filters = set()

        # create the main window widget
        self.main_widget = QMainWindow()
        self.setWidget(self.main_widget)
        
        # create the table and the menu
        self.table = None
        self.createTable(self.section)
        self.createMenus()

        # save manager object
        self.manager = manager

        self.show()
    
    def setRow(self, name : str, index : int, trace_data : TraceData, row : int):
        """Populate a row with trace item data.
        
            Params:
                name (str): the name of the trace
                index (int): the index of the trace in the contour
                trace_data (TraceData): the object containing the relevant trace data
                row (int): the row to modify
        """
        while row > self.table.rowCount()-1:
            self.table.insertRow(self.table.rowCount())
        col = 0
        self.table.setItem(row, col, QTableWidgetItem(name))
        col += 1
        if self.columns["Index"]:
            self.table.setItem(row, col, QTableWidgetItem(str(index)))
            col += 1
        if self.columns["Tags"]:
            self.table.setItem(row, col, QTableWidgetItem(", ".join(trace_data.getTags())))
            col += 1
        if self.columns["Length"]:
            self.table.setItem(row, col, QTableWidgetItem(str(round(trace_data.getLength(), 5))))
            col += 1
        if self.columns["Area"]:
            self.table.setItem(row, col, QTableWidgetItem(str(round(trace_data.getArea(), 5))))
            col += 1
        if self.columns["Radius"]:
            self.table.setItem(row, col, QTableWidgetItem(str(round(trace_data.getRadius(), 5))))
            col += 1
    
    def setContours(self, names):
        """Set the table data for a set of contours.
        
            Params:
                name (iterable): the names of contours to update
        """
        for name in names:
            # remove all existing traces associated with the contour in the table
            r = 0
            insert_row = None  # keep track of index where contours should be inserted
            while r < self.table.rowCount():
                trace_name = self.table.item(r, 0).text()
                if trace_name == name:
                    self.table.removeRow(r)
                else:
                    if insert_row is None and trace_name > name:
                        insert_row = r
                    r += 1
            if insert_row is None:
                insert_row = self.table.rowCount()
            
            # insert the new contour data
            trace_data_list = self.series.data.getTraceData(name, self.section.n)
            if trace_data_list:
                first_row = insert_row
                for trace_data in trace_data_list:
                    self.table.insertRow(insert_row)
                    self.setRow(name, insert_row - first_row, trace_data, insert_row)
                    insert_row += 1
    
    def createMenus(self):
        """Create the menu for the trace table widget."""
        # Create menubar menu
        menubar_list = [
            {
                "attr_name": "listmenu",
                "text": "List",
                "opts":
                [
                    ("columns_act", "Set columns...", "", self.setColumns),
                    ("export_act", "Export...", "", self.export),
                    {
                        "attr_name": "filtermenu",
                        "text": "Filter",
                        "opts":
                        [
                            ("refilter_act", "Regex filter...", "", self.setREFilter),
                            ("groupfilter_act", "Group filter...", "", self.setGroupFilter),
                            ("tagfilter_act", "Tag filter...", "", self.setTagFilter)
                        ]
                    }
                ]
            }
        ]
        # create the menubar object
        self.menubar = self.main_widget.menuBar()
        self.menubar.setNativeMenuBar(False) # attach menu to the window
        # fill in the menu bar object
        populateMenuBar(self, self.menubar, menubar_list)

        # create the right-click menu
        context_menu_list = [
            ("edit_act", "Edit...", "", self.editTraces),
            ("changeradius_act", "Change radius...", "", self.editRadius),
            None,
            ("hide_act", "Hide", "", self.hideTraces),
            ("unhide_act", "Unhide", "", lambda : self.hideTraces(hide=False)),
            None,
            ("find_act", "Find", "", self.findTrace),
            ("history_act", "View history", "", self.viewHistory),
            None,
            ("copy_act", "Copy", "", self.table.copy),
            None,
            ("delete_act", "Delete", "", self.deleteTraces)
        ]
        self.context_menu = QMenu(self)
        populateMenu(self, self.context_menu, context_menu_list)
            
    def passesFilters(self, name : str):
        """Check if an object passes the filters.
        
            Params:
                name (str): the name of the object
        """
        # check groups
        filters_len = len(self.group_filters)
        if filters_len != 0:
            object_groups = self.series.object_groups.getObjectGroups(name)
            groups_len = len(object_groups)
            union_len = len(object_groups.union(self.group_filters))
            if union_len == groups_len + filters_len:  # intersection does not exist
                return False
        
        # check tags
        filters_len = len(self.tag_filters)
        if filters_len != 0:
            object_tags = self.series.data.getTags(name)
            object_len = len(object_tags)
            union_len = len(object_tags.union(self.tag_filters))
            if union_len == object_len + filters_len:  # intersection does not exist
                return False
        
        # check regex
        for re_filter in self.re_filters:
            if bool(re.fullmatch(re_filter, name)):
                return True
        
        return False

    def getFilteredObjects(self):
        """Get the names of the objects that pass the filter."""
        filtered_object_list = []
        for name in self.series.data["objects"]:
            if self.passesFilters(name):
                filtered_object_list.append(name)
        
        return sorted(filtered_object_list)
    
    def format(self):
        """Format the rows and columns of the table."""
        self.table.resizeRowsToContents()
        for c in range(self.table.columnCount()):
            header = self.table.horizontalHeaderItem(c)
            if header != "Tags":
                self.table.resizeColumnToContents(c)
    
    def createTable(self, section : Section):
        """Create the table widget.
        
            Params:
                tracedict (dict): the dictionary containing the object table data objects
        """
        self.section = section

        # establish table headers
        self.horizontal_headers = ["Name"]
        for c in self.columns:
            if self.columns[c]:
                self.horizontal_headers.append(c)
        
        # filter the traces
        filtered_trace_names = self.getFilteredObjects()

        # create the table
        self.table = CopyTableWidget(0, len(self.horizontal_headers))

        # connect table functions
        self.table.contextMenuEvent = self.traceContextMenu
        self.table.mouseDoubleClickEvent = self.findTrace

        # format table
        self.table.setWordWrap(False)
        self.table.setShowGrid(False)  # no grid
        self.table.setAlternatingRowColors(True)  # alternate row colors
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # cannot be edited
        self.table.setHorizontalHeaderLabels(self.horizontal_headers)  # titles
        self.table.verticalHeader().hide()  # no veritcal header
        
        # fill in trace data
        self.setContours(filtered_trace_names)

        # format rows and columns
        self.format()

        # set table as central widget
        self.main_widget.setCentralWidget(self.table)
    
    def getSelectedItem(self):
        """Get the trace item that is selected by the user."""
        selected_indeces = self.table.selectedIndexes()
        if len(selected_indeces) != 1:
            return
        
        r = selected_indeces[0].row()
        name = self.table.item(r, 0).text()
        # iterate backwards to get index
        index = 0
        r -= 1
        while r >= 0 and self.table.item(r, 0).text() == name:
            r -= 1
            index += 1
        return name, index
    
    def getSelectedItems(self):
        """Get the trace items that iare selected by the user."""
        selected_indeces = self.table.selectedIndexes()
        if len(selected_indeces) < 1:
            return
        
        selected_traces = []
        for i in selected_indeces:
            r = i.row()
            name = self.table.item(r, 0).text()
            # iterate backwards to get index
            index = 0
            r -= 1
            while r >= 0 and self.table.item(r, 0).text() == name:
                r -= 1
                index += 1
            selected_traces.append((name, index))
        
        return selected_traces
    
    def resizeEvent(self, event):
        """Resize the table when window is resized."""
        super().resizeEvent(event)
        w = event.size().width()
        h = event.size().height()
        self.table.resize(w, h-20)

    # RIGHT CLICK FUNCTIONS

    def editTraces(self):
        """Edit a set of traces."""
        items = self.getSelectedItems()
        if items is None:
            return
        
        traces = self.manager.getTraces(items)
        
        new_attr, confirmed = TraceDialog(
            self,
            traces
        ).exec()
        if not confirmed:
            return
        
        self.manager.editTraces(
            traces,
            new_attr.name,
            new_attr.color,
            new_attr.tags,
            new_attr.fill_mode
        )
        self.manager.update()
    
    def hideTraces(self, hide=True):
        """Hide a set of traces.
        
            Params:
                hide (bool): True if the traces should be hidden
        """
        items = self.getSelectedItems()
        if items is None:
            return
        
        traces = self.manager.getTraces(items)
        self.manager.hideTraces(traces, hide)
    
    def editRadius(self):
        """Edit the radius for a set of traces."""
        items = self.getSelectedItems()
        if items is None:
            return
        
        traces = self.manager.getTraces(items)

        existing_radius = round(traces[0].getRadius(), 7)

        for trace in traces[1:]:
            if abs(existing_radius - trace.getRadius()) > 1e-6:
                existing_radius = ""
                break
        
        new_rad, confirmed = QInputDialog.getText(
            self,
            "New Trace Radius",
            "Enter the new trace radius:",
            text=str(existing_radius)
        )
        if not confirmed:
            return
        try:
            new_rad = float(new_rad)
        except ValueError:
            return
        
        self.manager.editRadius(traces, new_rad)
        self.manager.update()
          
    def findTrace(self, event=None):
        """Select a trace on the section."""
        item = self.getSelectedItem()
        if item is None:
            return
        self.manager.findTrace(item)
    
    def deleteTraces(self):
        """Delete a set of traces."""
        items = self.getSelectedItems()
        if not items:
            return
        
        traces = self.manager.getTraces(items)

        self.manager.deleteTraces(traces) 
        self.manager.update()
    
    def viewHistory(self):
        """View the history of a set of traces."""
        items = self.getSelectedItems()
        if not items:
            return
        
        traces = self.manager.getTraces(items)

        self.manager.viewHistory(traces)
    
    def traceContextMenu(self, event=None):
        """Executed when button is right-clicked: pulls up menu for user to modify traces."""
        if len(self.table.selectedIndexes()) == 0:
            return
        self.context_menu.exec(event.globalPos())

    # MENU-RELATED FUNCTIONS
    
    def setColumns(self):
        """Set the columns to display."""
        new_cols, confirmed = TableColumnsDialog(
            self,
            self.columns
        ).exec()
        if not confirmed:
            return
        self.columns = new_cols
        
        self.manager.updateTable(self)
    
    def export(self):
        """Export the trace list as a csv file."""
        # get the location from the user
        global fd_dir
        file_path, ext = QFileDialog.getSaveFileName(
            self,
            "Save Trace List",
            os.path.join(fd_dir.get(), "traces.csv"),
            filter="Comma Separated Values (*.csv)"
        )
        if not file_path:
            return
        else:
            fd_dir.set(os.path.dirname(file_path))
        # unload the table into the csv file
        csv_file = open(file_path, "w")
        # headers first
        items = []
        for c in range(self.table.columnCount()):
            items.append(self.table.horizontalHeaderItem(c).text())
        csv_file.write(",".join(items) + "\n")
        # trace data
        for r in range(self.table.rowCount()):
            items = []
            for c in range(self.table.columnCount()):
                items.append(self.table.item(r, c).text())
            csv_file.write(",".join(items) + "\n")
        # close file
        csv_file.close()        
    
    def setREFilter(self):
        """Set a new regex filter for the list."""
        # get a new filter from the user
        re_filter_str = ", ".join(self.re_filters)
        new_re_filter, confirmed = QInputDialog.getText(
            self,
            "Filter Traces",
            "Enter the trace filters:",
            text=re_filter_str
        )
        if not confirmed:
            return

        # get the new regex filter for the set
        self.re_filters = new_re_filter.split(", ")
        if self.re_filters == [""]:
            self.re_filters = [".*"]
        for i, filter in enumerate(self.re_filters):
            self.re_filters[i] = filter.replace("#", "[0-9]")
        self.re_filters = set(self.re_filters)

        # call through manager to update self
        self.manager.updateTable(self)
    
    def setGroupFilter(self):
        """Set a new group filter for the list."""
        # get a new filter from the user
        group_filter_str = ", ".join(self.group_filters)
        new_group_filter, confirmed = QInputDialog.getText(
            self,
            "Filter Traces",
            "Enter the group filters:",
            text=group_filter_str
        )
        if not confirmed:
            return

        # get the new group filter for the list
        self.group_filters = new_group_filter.split(", ")
        if self.group_filters == [""]:
            self.group_filters = set()
        else:
            self.group_filters = set(self.group_filters)
        
        # call through manager to update self
        self.manager.updateTable(self)
    
    def setTagFilter(self):
        """Set a new tag filter for the list."""
        # get a new filter from the user
        tag_filter_str = ", ".join(self.tag_filters)
        new_tag_filter, confirmed = QInputDialog.getText(
            self,
            "Filter Traces",
            "Enter the tag filters:",
            text=tag_filter_str
        )
        if not confirmed:
            return

        # get the new tag filter for the list
        self.tag_filters = new_tag_filter.split(", ")
        if self.tag_filters == [""]:
            self.tag_filters = set()
        else:
            self.tag_filters = set(self.tag_filters)
        
        # call through manager to update self
        self.manager.updateTable(self)

    def closeEvent(self, event):
        """Remove self from manager table list."""
        self.manager.tables.remove(self)
        super().closeEvent(event)
