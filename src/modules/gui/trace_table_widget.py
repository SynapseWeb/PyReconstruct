import re

from PySide6.QtWidgets import (
    QMainWindow, 
    QDockWidget, 
    QTableWidget, 
    QTableWidgetItem, 
    QAbstractItemView, 
    QWidget, 
    QInputDialog, 
    QMenu, 
    QFileDialog
)
from PySide6.QtCore import Qt

from modules.pyrecon.series import Series

from modules.backend.trace_table_item import TraceTableItem
from modules.gui.gui_functions import populateMenuBar, populateMenu

from modules.gui.dialog import TableColumnsDialog, TraceDialog

class TraceTableWidget(QDockWidget):

    def __init__(self, series : Series, tracedict : dict, mainwindow : QWidget, manager):
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
        self.createTable(tracedict)
        self.createMenus()

        # save manager object
        self.manager = manager

        self.show()
    
    def setRow(self, traceitem : TraceTableItem, row : int):
        """Populate a row with trace item data.
        
            Params:
                traceitem (TraceTableItem): the object contianing the trace table data
                row (int): the row to modify
        """
        while row > self.table.rowCount()-1:
            self.table.insertRow(self.table.rowCount())
        col = 0
        self.table.setItem(row, col, QTableWidgetItem(traceitem.name))
        col += 1
        if self.columns["Index"]:
            self.table.setItem(row, col, QTableWidgetItem(str(traceitem.index)))
            col += 1
        if self.columns["Tags"]:
            self.table.setItem(row, col, QTableWidgetItem(", ".join(traceitem.getTags())))
            col += 1
        if self.columns["Length"]:
            self.table.setItem(row, col, QTableWidgetItem(str(round(traceitem.getLength(), 5))))
            col += 1
        if self.columns["Area"]:
            self.table.setItem(row, col, QTableWidgetItem(str(round(traceitem.getArea(), 5))))
            col += 1
        if self.columns["Radius"]:
            self.table.setItem(row, col, QTableWidgetItem(str(round(traceitem.getRadius(), 5))))
            col += 1
    
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
                            ("groupfilter_act", "Group fiter...", "", self.setGroupFilter),
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
            ("delete_act", "Delete", "", self.deleteTraces)
        ]
        self.context_menu = QMenu(self)
        populateMenu(self, self.context_menu, context_menu_list)
            
    def passesFilters(self, item : TraceTableItem):
        """Determine if a trace will be displayed in the table based on existing filters.
        
            Params:
                item (TraceTableItem): the item containing the data
        """
        # check groups
        filters_len = len(self.group_filters)
        if filters_len != 0:
            object_groups = self.series.object_groups.getObjectGroups(item.name)
            groups_len = len(object_groups)
            union_len = len(object_groups.union(self.group_filters))
            if union_len == groups_len + filters_len:  # intersection does not exist
                return False
        
        # check tags
        filters_len = len(self.tag_filters)
        if filters_len != 0:
            trace_tags = item.getTags()
            trace_len = len(trace_tags)
            union_len = len(trace_tags.union(self.tag_filters))
            if union_len == trace_len + filters_len:  # intersection does not exist
                return False
        
        # check regex (will only be run if passes groups and tags)
        for re_filter in self.re_filters:
            if bool(re.fullmatch(re_filter, item.name)):
                return True
        return False
    
    def format(self):
        """Format the rows and columns of the table."""
        self.table.resizeRowsToContents()
        for c in range(self.table.columnCount()):
            header = self.table.horizontalHeaderItem(c)
            if header != "Tags":
                self.table.resizeColumnToContents(c)
    
    def createTable(self, tracedict : dict):
        """Create the table widget.
        
            Params:
                tracedict (dict): the dictionary containing the object table data objects
        """
        # establish table headers
        self.horizontal_headers = ["Name"]
        for c in self.columns:
            if self.columns[c]:
                self.horizontal_headers.append(c)
        
        # filter the traces
        sorted_trace_names = sorted(list(tracedict.keys()))
        self.items = []
        for name in sorted_trace_names:
            for item in tracedict[name]:
                if self.passesFilters(item):
                    self.items.append(item)

        # create the table
        self.table = QTableWidget(0, len(self.horizontal_headers))

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
        for r, item in enumerate(self.items):
            self.setRow(item, r)

        # format rows and columns
        self.format()

        # set table as central widget
        self.main_widget.setCentralWidget(self.table)
    
    def addItem(self, new_item : TraceTableItem):
        """Add an item to the table.
        
            Params:
                new_item (TraceTableItem): the item to add to the table
        """
        if not self.passesFilters(new_item):
            return
        
        # find new place for the item
        r = 0
        while r < len(self.items) and self.items[r].name <= new_item.name:
            r += 1
        # insert the item
        self.items.insert(r, new_item)
        self.table.insertRow(r)
        self.setRow(new_item, r)

        # first item added
        if len(self.items) == 1:
            self.format()
    
    def removeItem(self, del_item : TraceTableItem):
        """Remove an item from the table.
        
            Parmas:
                del_item (TraceTableItem): the item to delete
        """
        # find the item in the list
        try:
            r = self.items.index(del_item)
        except ValueError:
            return
        # remove the item
        self.items.remove(del_item)
        self.table.removeRow(r)
        while r < len(self.items) and self.items[r].name == del_item.name:
            self.setRow(self.items[r], r)
            r += 1
    
    def getSelectedItem(self):
        """Get the trace item that is selected by the user."""
        selected_indeces = self.table.selectedIndexes()
        if len(selected_indeces) != 1:
            return
        return self.items[selected_indeces[0].row()]
    
    def getSelectedItems(self):
        """Get the trace items that iare selected by the user."""
        selected_indeces = self.table.selectedIndexes()
        if len(selected_indeces) < 1:
            return
        return [
            self.items[i.row()] for i in selected_indeces
        ]    
    
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
        
        name, color, tags, mode = new_attr
        self.manager.editTraces(name, color, tags, mode, traces)
        self.manager.loadSection()
    
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

        existing_radius = str(round(traces[0].getRadius(), 7))

        for trace in traces[1:]:
            if abs(existing_radius - trace.getRadius()) > 1e-6:
                existing_radius = ""
                break
        
        new_rad, confirmed = QInputDialog.getText(
            self,
            "New Trace Radius",
            "Enter the new trace radius:",
            text=existing_radius
        )
        if not confirmed:
            return
        try:
            new_rad = float(new_rad)
        except ValueError:
            return
        
        self.manager.editRadius(new_rad, traces)
        self.manager.loadSection()
          
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
        self.manager.loadSection()
    
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
        file_path, ext = QFileDialog.getSaveFileName(
            self,
            "Save Trace List",
            "traces.csv",
            filter="Comma Separated Values (.csv)"
        )
        if not file_path:
            return
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