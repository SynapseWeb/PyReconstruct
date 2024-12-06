import re
import os

from PySide6.QtWidgets import (
    QTableWidgetItem, 
    QWidget, 
    QInputDialog, 
    QMenu
)
from PySide6.QtCore import Qt

from .data_table import DataTable
from PyReconstruct.modules.gui.utils import sortList

from PyReconstruct.modules.datatypes import (
    Series,
    Section
)
from PyReconstruct.modules.gui.utils import (
    populateMenuBar,
    populateMenu,
    notify
)
from PyReconstruct.modules.gui.dialog import (
    TraceDialog,
    ShapesDialog,
    QuickDialog,
    FileDialog
)

class TraceTableWidget(DataTable):

    def __init__(self, series : Series, section : Section, mainwindow : QWidget, manager):
        """Create the trace table dock widget.
        
            Params:
                series (Series): the series object
                contourdict (dict): contains all trace info for the table
                mainwindow (QWidget): the main window the dock is connected to
                manager: the trace table manager
        """
        self.section = section

        self.re_filters = set([".*"])
        self.tag_filters = set()
        self.group_filters = set()
        self.hide_filter = "all"

        self.temp_selected = None  # indicates items that were checked--this overrides selected items in the table ONCE

        super().__init__("trace", series, mainwindow, manager)
        self.static_columns = ["Name"]
        self.rows = []
        self.createTable(self.section)

        self.show()
    
    def getItems(self, name_trace_data : tuple, item_type : str):
        """Populate a row with trace item data.
        
            Params:
                name_trace_data (tuple): the tuple container for the (name, TraceData) objects
                item_type (str): the specific data to be retrieved
        """
        name, trace_data = name_trace_data
        items = []

        if item_type == "Name":
            
            items.append(QTableWidgetItem(name))
            
        elif item_type == "Index":
            
            items.append(QTableWidgetItem(str(trace_data.index)))
            
        elif item_type == "Tags":
            
            items.append(QTableWidgetItem(", ".join(trace_data.getTags())))
            
        elif item_type == "Hidden":
            
            item = QTableWidgetItem("")
            
            item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            item.setCheckState(Qt.CheckState.Checked if trace_data.hidden else Qt.CheckState.Unchecked)
            items.append(item)
            
        elif item_type == "Closed":
            
            item = QTableWidgetItem("")
            item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            item.setCheckState(Qt.CheckState.Checked if trace_data.closed else Qt.CheckState.Unchecked)
            items.append(item)
            
        elif item_type == "Length":
            
            items.append(QTableWidgetItem(str(round(trace_data.getLength(), 5))))
            
        elif item_type == "Area":
            
            items.append(QTableWidgetItem(str(round(trace_data.getArea(), 5))))
            
        elif item_type == "Radius":
            
            items.append(QTableWidgetItem(str(round(trace_data.getRadius(), 5))))

        elif item_type == "Centroid":

            centroid_x, centroid_y = trace_data.getCentroid()

            items.extend(
                (QTableWidgetItem(str(round(centroid_x, 5))),
                 QTableWidgetItem(str(round(centroid_y, 5))))
            )
            
        elif item_type == "Feret":
            
            feret_min, feret_max = trace_data.getFeret()

            items.extend(
                (QTableWidgetItem(str(round(feret_max, 5))),
                 QTableWidgetItem(str(round(feret_min, 5))))
            )

        return items
    
    def passesFilters(self, name_trace_data : tuple):
        """Check if an object passes the filters.
        
            Params:
                name_trace_data (tuple): the name, TraceData of the trace
        """
        name, trace_data = name_trace_data

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
            trace_tags = trace_data.getTags()
            trace_len = len(trace_tags)
            union_len = len(trace_tags.union(self.tag_filters))
            if union_len == trace_len + filters_len:  # intersection does not exist
                return False
        
        # check hidden
        h = trace_data.hidden
        if self.hide_filter == "hidden" and not h:
            return False
        elif self.hide_filter == "unhidden" and h:
            return False
        
        # check regex
        passes_filters = False if self.re_filters else True
        for re_filter in self.re_filters:
            if bool(re.fullmatch(re_filter, name)):
                passes_filters = True
        if not passes_filters:
            return False
        
        return True

    def getPassingTraces(self, contour_name : str):
        """Get the name, TraceData pairs for the passing traces of a certain contour.
        
            Params:
                contour_name (str): the name of the contour
        """
        trace_data_list = self.series.data.getTraceData(contour_name, self.section.n)
        if not trace_data_list:
            return []
        
        trace_data_list.sort()  # sort by trace index
        passing = []
        for trace_data in trace_data_list:
            if self.passesFilters((contour_name, trace_data)):
                passing.append((contour_name, trace_data))
        return passing

    def getFiltered(self):
        """Get the names of the objects that pass the filter."""
        contour_names = sortList(list(self.section.contours.keys()))
        filtered = []

        for name in contour_names:
            filtered += self.getPassingTraces(name)
        
        return filtered
    
    def setRow(self, name_trace_data : tuple, row : int, resize=True):
        """Set the data for a row of the table.
        
            Params:
                name_trace_data (tuple): the container for the necessary data
                row (int): the row to enter this data into
        """
        name, trace_data = name_trace_data
        while row >= self.table.rowCount():
            self.table.insertRow(self.table.rowCount())
        while row >= len(self.rows):
            self.rows.append(None)
        self.rows[row] = trace_data

        super().setRow(name_trace_data, row, resize)
    
    def updateData(self, names, resize=True):
        """Set the table data for a set of contours.
        
            Params:
                name (iterable): the names of contours to update
        """
        for name in names:
            # remove existing instances
            r, is_in_table = self.table.getRowIndex(name)
            if is_in_table:
                i = self.table.item(r, 0)
                while i and i.text() == name:
                    self.table.removeRow(r)
                    self.rows.pop(r)
                    i = self.table.item(r, 0)
            
            # get new instances
            passing = self.getPassingTraces(name)
            modified_rows = []
            for name_trace_data in passing:
                self.table.insertRow(r)
                self.rows.insert(r, None)
                self.setRow(name_trace_data, r)
                modified_rows.append(r)
                r += 1
                      
            if resize:
                self.table.resizeColumnsToContents()
                for r in modified_rows:
                    self.table.resizeRowToContents(r)

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
                    ("exportall_act", "Export all traces in series...", "", self.exportAll)
                ]
            },
            {
                "attr_name": "filtermenu",
                "text": "Filter",
                "opts":
                [
                    ("refilter_act", "Regex filter...", "", self.setREFilter),
                    ("groupfilter_act", "Group filter...", "", self.setGroupFilter),
                    ("tagfilter_act", "Tag filter...", "", self.setTagFilter),
                    ("hidefilter_act", "Hide filter...", "", self.setHideFilter)
                ]
            }
        ]
        # create the menubar object
        self.menubar = self.main_widget.menuBar()
        self.menubar.clear()
        self.menubar.setNativeMenuBar(False) # attach menu to the window
        # fill in the menu bar object
        populateMenuBar(self, self.menubar, menubar_list)

        # create the right-click menu
        context_menu_list = self.mainwindow.field.getTraceMenu(is_in_field=False)
        self.context_menu = QMenu(self)
        populateMenu(self, self.context_menu, context_menu_list)

    def updateTitle(self):
        """Update the title of the table."""
        is_regex = tuple(self.re_filters) != (".*",)
        is_tag = bool(self.tag_filters)
        is_group = bool(self.group_filters)

        title = "Trace List "
        if any((is_regex, is_tag, is_group)):
            strs = []
            if is_regex: strs.append("regex")
            if is_tag: strs.append("tags")
            if is_group: strs.append("groups")
            title += f"(Filtered by: {', '.join(strs)})"
        
        self.setWindowTitle(title)

    def getHeaders(self):
        """Get the headers for the table."""
        headers_to_display = self.static_columns.copy()
        for col_group, checked in self.columns:
            if not checked:
                continue
            elif col_group == "Centroid":
                headers_to_display.extend(("Centroid-x", "Centroid-y"))
            elif col_group == "Feret":
                headers_to_display.extend(("Feret-Max", "Feret-Min"))
            else:
                headers_to_display.append(col_group)
        return headers_to_display
    
    def createTable(self, section : Section):
        """Create the table.
        
            Params:
                section (Section): the section the table is displaying data for
        """
        self.section = section
        super().createTable()
    
    def itemChanged(self, item : QTableWidgetItem):
        """Called when user checks a checkbox in the table."""
        # prevent recursion
        if not self.process_check_event:
            return
        self.process_check_event = False

        c = item.column()
        state = item.checkState()
        value = state == Qt.CheckState.Checked
        r = item.row()
        name = self.table.item(r, 0).text()
        index = self.rows[r].index

        # check if object is locked
        if self.series.getAttr(name, "locked"):
            unlocked = self.mainwindow.field.notifyLocked(name)
            if not unlocked:
                return

        if self.horizontal_headers[c] == "Hidden":
            self.temp_selected = [(name, index)]
            self.mainwindow.field.hideTraces(hide=value)
        elif self.horizontal_headers[c] == "Closed":
            self.temp_selected = [(name, index)]
            self.mainwindow.field.closeTraces(closed=value)

        self.process_check_event = True
    
    def getSelected(self, include_locked=False, single=False):
        """Get the trace items that are selected by the user."""
        # check if user checked an item recently
        if self.temp_selected:
            selected_items = self.temp_selected.copy()
            self.temp_selected = None
            return selected_items
        
        selected_indeces = self.table.selectedIndexes()
        if len(selected_indeces) < 1:
            return
        
        selected_traces = []
        locked_objs = set()
        for i in selected_indeces:
            r = i.row()
            name = self.table.item(r, 0).text()
            index = self.rows[r].index
            if not include_locked and self.series.getAttr(name, "locked"):
                locked_objs.add(name)
            selected_traces.append((name, index))
        
        if single and len(selected_traces) != 1:
            notify("Please select only one trace for this option.")
            return
        
        if locked_objs:
            unlocked = self.mainwindow.field.notifyLocked(locked_objs)
            if not unlocked:
                return
        
        if single:
            return selected_traces[0]
        else:
            return selected_traces
    
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
          
    def findTrace(self):
        """Select a trace on the section."""
        item = self.getSelected(include_locked=True, single=True)
        if item is None:
            return
        name, index = item
        self.mainwindow.field.findTrace(name, index)

    def mouseDoubleClickEvent(self, event=None):
        """Called when mouse is double-clicked."""
        super().mouseDoubleClickEvent(event)
        self.findTrace()
    
    def backspace(self):
        """Called when backspace is pressed."""
        self.mainwindow.field.deleteTraces()
    
    def traceContextMenu(self, event=None):
        """Executed when button is right-clicked: pulls up menu for user to modify traces."""
        if not self.getSelected():
            return
        
        self.context_menu.exec(event.globalPos())

    #### Menu-related functions ############################################

    def exportAll(self):
        """Export the trace list as a csv file."""
        # get the location from the user
        file_path = FileDialog.get(
            "save",
            self,
            "Save List of All Traces",
            file_name="traces.csv",
            filter="Comma Separated Values (*.csv)"
        )
        if not file_path: return

        self.series.data.exportTracesCSV(file_path)     
    
    def setREFilter(self):
        """Set a new regex filter for the list."""
        # get a new filter from the user
        structure = [
            ["Enter the regex filter(s) below"],
            [("multitext", self.re_filters)]
        ]
        response, confirmed = QuickDialog.get(self, structure, "Regex Filters")
        if not confirmed:
            return
        
        self.re_filters = set(response[0] if response[0] else [".*"])
        self.re_filters = set([s.replace("#", "[0-9]") for s in self.re_filters])

        # call through manager to update self
        self.manager.recreateTable(self)
    
    def setGroupFilter(self):
        """Set a new group filter for the list."""
        # get a new filter from the user
        structure = [
            ["Enter the group filter(s) below"],
            [("multitext", self.group_filters)]
        ]
        response, confirmed = QuickDialog.get(self, structure, "Group Filters")
        if not confirmed:
            return
        
        self.group_filters = set(response[0])
        
        # call through manager to update self
        self.manager.recreateTable(self)
    
    def setTagFilter(self):
        """Set a new tag filter for the list."""
        # get a new filter from the user
        structure = [
            ["Enter the tag filter(s) below"],
            [("multitext", self.tag_filters)]
        ]
        response, confirmed = QuickDialog.get(self, structure, "Tag Filters")
        if not confirmed:
            return
        
        self.tag_filters = set(response[0])
        
        # call through manager to update self
        self.manager.recreateTable(self)
    
    def setHideFilter(self):
        """Set the hidden trace filter for the list."""
        structure = [
            ["Display:"],
            [("radio",
              ("all traces", self.hide_filter == "all"),
              ("only hidden traces", self.hide_filter == "hidden"),
              ("only unhidden traces", self.hide_filter == "unhidden")
            )]
        ]
        response, confirmed = QuickDialog.get(self, structure, "Hide Filter")
        if not confirmed:
            return
        
        if response[0][0][1]: self.hide_filter = "all"
        elif response[0][1][1]: self.hide_filter = "hidden"
        else: self.hide_filter = "unhidden"

        # call through manager to update self
        self.manager.recreateTable(self)
