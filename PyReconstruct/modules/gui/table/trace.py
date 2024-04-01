import re
import os

from PySide6.QtWidgets import (
    QMainWindow, 
    QDockWidget, 
    QTableWidgetItem, 
    QAbstractItemView, 
    QWidget, 
    QInputDialog, 
    QMenu
)
from PySide6.QtCore import Qt

from .copy_table_widget import CopyTableWidget
from .str_helper import sortList

from PyReconstruct.modules.datatypes import (
    Series,
    Section,
    TraceData
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
        self.columns = self.series.getOption("trace_columns")
        # check for missing columns
        defaults = self.series.getOption("trace_columns", get_default=True)
        for col_name in defaults:
            if col_name not in self.columns:
                self.columns = defaults
                self.series.setOption("trace_columns", self.columns)
                break

        self.re_filters = set([".*"])
        self.tag_filters = set()
        self.group_filters = set()
        self.hide_filter = "all"

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
    
    def setRow(self, name : str, trace_data : TraceData, row : int, resize_columns=True):
        """Populate a row with trace item data.
        
            Params:
                name (str): the name of the trace
                index (int): the index of the trace in the contour
                trace_data (TraceData): the object containing the relevant trace data
                row (int): the row to modify
        """
        while row > self.table.rowCount()-1:
            self.table.insertRow(self.table.rowCount())
            self.rows.append(None)
        self.rows[row] = trace_data
        col = 0
        self.table.setItem(row, col, QTableWidgetItem(name))
        col += 1
        if self.columns["Index"]:
            self.table.setItem(row, col, QTableWidgetItem(str(trace_data.index)))
            col += 1
        if self.columns["Tags"]:
            self.table.setItem(row, col, QTableWidgetItem(", ".join(trace_data.getTags())))
            col += 1
        if self.columns["Hidden"]:
            self.enable_cb_event = False
            item = QTableWidgetItem("")
            item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            item.setCheckState(Qt.CheckState.Checked if trace_data.hidden else Qt.CheckState.Unchecked)
            self.table.setItem(row, col, item)
            self.enable_cb_event = True
            col += 1
        if self.columns["Closed"]:
            self.enable_cb_event = False
            item = QTableWidgetItem("")
            item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            item.setCheckState(Qt.CheckState.Checked if trace_data.closed else Qt.CheckState.Unchecked)
            self.table.setItem(row, col, item)
            self.enable_cb_event = True
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
    
    def setContours(self, names, resize=True):
        """Set the table data for a set of contours.
        
            Params:
                name (iterable): the names of contours to update
        """
        filters_len = len(self.tag_filters)  # use to later check tags
        for name in names:
            r, is_in_table = self.table.getRowIndex(name)

            # remove existing instances
            if is_in_table:
                i = self.table.item(r, 0)
                while i and i.text() == name:
                    self.table.removeRow(r)
                    self.rows.pop(r)
                    i = self.table.item(r, 0)
            
            # insert the new contour data
            trace_data_list = self.series.data.getTraceData(name, self.section.n)
            modified_rows = []
            if trace_data_list:
                first_row = r
                for trace_data in trace_data_list:
                    # check for tags
                    if filters_len != 0:
                        trace_tags = trace_data.getTags()
                        trace_len = len(trace_tags)
                        union_len = len(trace_tags.union(self.tag_filters))
                        if union_len == trace_len + filters_len:  # intersection does not exist
                            continue
                    # check for hidden
                    if (
                        (self.hide_filter == "hidden" and not trace_data.hidden) or
                        (self.hide_filter == "unhidden" and trace_data.hidden)
                    ):
                        continue
                    self.table.insertRow(r)
                    self.rows.insert(r, None)
                    self.setRow(name, trace_data, r)
                    modified_rows.append(r)
                    r += 1            
            if resize:
                self.table.resizeColumnsToContents()
                for r in modified_rows:
                    self.table.resizeRowToContents(r)
    
    def itemChecked(self, item : QTableWidgetItem):
        """Called when user checks a checkbox in the table."""
        # prevent recursion
        if not self.enable_cb_event:
            return
        self.enable_cb_event = False

        c = item.column()
        state = item.checkState()
        value = state == Qt.CheckState.Checked
        name, index = self.getSelectedItem(item)

        if name:
            items = [(name, index)]
            if self.horizontal_headers[c] == "Hidden":
                self.hideTraces(value, items)
            elif self.horizontal_headers[c] == "Closed":
                self.closeTraces(value, items)
        else:
            item.setCheckState(Qt.CheckState.Unchecked if value else Qt.CheckState.Checked)


        self.enable_cb_event = True

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
        self.menubar.setNativeMenuBar(False) # attach menu to the window
        # fill in the menu bar object
        populateMenuBar(self, self.menubar, menubar_list)

        # create the right-click menu
        context_menu_list = [
            ("edit_act", "Edit...", "", self.editTraces),
            {
                "attr_name": "stampmenu",
                "text": "Stamp attributes",
                "opts":
                [
                    ("changeradius_act", "Edit radius...", "", self.editRadius),
                    ("changeshape_act", "Edit shape...", "", self.editShape)
                ]
            },
            None,
            ("hide_act", "Hide", "", self.hideTraces),
            ("unhide_act", "Unhide", "", lambda : self.hideTraces(hide=False)),
            None,
            ("find_act", "Find", "", self.findTrace),
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
        passes_filters = False if self.re_filters else True
        for re_filter in self.re_filters:
            if bool(re.fullmatch(re_filter, name)):
                passes_filters = True
        if not passes_filters:
            return False
        
        return True

    def getFilteredObjects(self):
        """Get the names of the objects that pass the filter."""
        filtered_object_list = []
        for name in self.series.data["objects"]:
            if self.passesFilters(name):
                filtered_object_list.append(name)
        
        return sortList(filtered_object_list)

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
    
    def createTable(self, section : Section):
        """Create the table widget.
        
            Params:
                tracedict (dict): the dictionary containing the object table data objects
        """
        # close an existing table and save scroll position
        if self.table is not None:
            vscroll = self.table.verticalScrollBar()
            scroll_pos = vscroll.value()
            self.table.close()
        else:
            scroll_pos = 0
        
        self.section = section

        self.updateTitle()

        # establish table headers
        self.horizontal_headers = ["Name"]
        for c in self.columns:
            if self.columns[c]:
                self.horizontal_headers.append(c)
        
        # filter the traces
        filtered_trace_names = self.getFilteredObjects()

        # create the table
        self.table = CopyTableWidget(0, len(self.horizontal_headers))
        self.rows = []

        # connect table functions
        self.table.contextMenuEvent = self.traceContextMenu
        self.table.mouseDoubleClickEvent = self.findTrace
        self.table.backspace = self.deleteTraces

        # format table
        self.table.setWordWrap(False)
        self.table.setShowGrid(False)  # no grid
        self.table.setAlternatingRowColors(True)  # alternate row colors
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # cannot be edited
        self.table.setHorizontalHeaderLabels(self.horizontal_headers)  # titles
        self.table.verticalHeader().hide()  # no veritcal header
        
        # fill in trace data
        self.setContours(filtered_trace_names, resize=False)

        # format rows and columns
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

        # set the saved scroll value
        self.table.verticalScrollBar().setValue(scroll_pos)

        # set table as central widget
        self.main_widget.setCentralWidget(self.table)

        # checkbox for hidden and closed
        self.table.itemChanged.connect(self.itemChecked)
        self.enable_cb_event = True
    
    def getSelectedItem(self, item : QTableWidgetItem=None, include_locked=False):
        """Get the trace item that is selected by the user."""
        if item is None:
            selected_indeces = self.table.selectedIndexes()
            if len(selected_indeces) != 1:
                return None, None
            item = selected_indeces[0]
        
        r = item.row()
        name = self.table.item(r, 0).text()
        index = self.rows[r].index

        if not include_locked and self.series.getAttr(name, "locked"):
            unlocked = self.mainwindow.field.notifyLocked(name)
            if not unlocked:
                return None, None

        return name, index
    
    def getSelectedItems(self, include_locked=False):
        """Get the trace items that iare selected by the user."""
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
        
        if locked_objs:
            unlocked = self.mainwindow.field.notifyLocked(locked_objs)
            if not unlocked:
                return None
        
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
        
        new_attrs, confirmed = TraceDialog(
            self,
            traces
        ).exec()
        if not confirmed:
            return
        
        self.manager.editTraces(
            traces,
            new_attrs.name,
            new_attrs.color,
            new_attrs.tags,
            new_attrs.fill_mode
        )
        self.manager.update()
    
    def hideTraces(self, hide=True, items=None):
        """Hide a set of traces.
        
            Params:
                hide (bool): True if the traces should be hidden
                items (list): the specific items indicating the traces to modify
        """
        if items is None:
            items = self.getSelectedItems()
        if not items:
            return
        
        traces = self.manager.getTraces(items)
        self.manager.hideTraces(traces, hide)
    
    def closeTraces(self, closed=True, items=None):
        """Close a set of traces.
        
            Params:
                closed (bool): True if the traces should be closed
                items (list): the specific items indicating the traces to modify
        """
        if items is None:
            items = self.getSelectedItems()
        if not items:
            return
        
        traces = self.manager.getTraces(items)
        self.manager.closeTraces(traces, closed)
    
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
    
    def editShape(self):
        """Modify the shape of the traces on an entire object."""
        items = self.getSelectedItems()
        if items is None:
            return
        
        traces = self.manager.getTraces(items)
        
        new_shape, confirmed = ShapesDialog(self).exec()
        if not confirmed:
            return
        
        self.manager.editShape(traces, new_shape)
        self.manager.update()
          
    def findTrace(self, event=None):
        """Select a trace on the section."""
        item = self.getSelectedItem(include_locked=True)
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
    
    def traceContextMenu(self, event=None):
        """Executed when button is right-clicked: pulls up menu for user to modify traces."""
        if not self.getSelectedItems():
            return
        
        self.context_menu.exec(event.globalPos())

    # MENU-RELATED FUNCTIONS
    
    def setColumns(self):
        """Set the columns to display."""
        structure = [
            [("check", *tuple(self.columns.items()))]
        ]
        response, confirmed = QuickDialog.get(self, structure, "Table Columns")
        if not confirmed:
            return
        
        self.columns = dict(response[0])
        self.series.setOption("trace_columns", self.columns)
        self.manager.updateTable(self)
    
    def export(self):
        """Export the trace list as a csv file."""
        # get the location from the user
        file_path = FileDialog.get(
            "save",
            self,
            "Save Trace List",
            file_name="traces.csv",
            filter="Comma Separated Values (*.csv)"
        )
        if not file_path: return
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
        self.manager.updateTable(self)
    
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
        self.manager.updateTable(self)
    
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
        self.manager.updateTable(self)
    
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
        self.manager.updateTable(self)

    def closeEvent(self, event):
        """Remove self from manager table list."""
        self.manager.tables.remove(self)
        super().closeEvent(event)
