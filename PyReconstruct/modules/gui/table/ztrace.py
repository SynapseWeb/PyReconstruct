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
)
from PySide6.QtCore import Qt

from .copy_table_widget import CopyTableWidget
from .str_helper import sortList

from PyReconstruct.modules.datatypes import Series
from PyReconstruct.modules.gui.utils import (
    populateMenuBar,
    populateMenu,
    notify
)
from PyReconstruct.modules.gui.dialog import (
    QuickDialog,
    ObjectGroupDialog,
    FileDialog
)

class ZtraceTableWidget(QDockWidget):

    def __init__(self, series : Series, mainwindow : QWidget, manager):
        """Create the object table dock widget.
        
            Params:
                series (Series): the series object
                mainwindow (QWidget): the main window the dock is connected to
                manager: the object table manager
        """
        # initialize the widget
        super().__init__(mainwindow)
        self.mainwindow = mainwindow
        self.series = series
        self.series_states = self.mainwindow.field.series_states

        # set desired format for widget
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)  # ccan be docked to right or left side
        self.setWindowTitle("Ztrace List")

        self.re_filters = set([".*"])
        self.group_filters = set()

        # create the main window widget
        self.main_widget = QMainWindow()
        self.setWidget(self.main_widget)
        
        # create the table and the menu
        self.table = None
        self.createTable()
        self.createMenus()

        # save manager object
        self.manager = manager

        self.show()
    
    def setRow(self, ztrace_name : str, row : int, resize=True):
        """Populate a row with trace item data.
        
            Params:
                ztrace_name (str): the name of the ztrace
                row (int): the row to insert the data
        """
        if ztrace_name not in self.series.ztraces:
            self.table.removeRow(row)
        else:
            while row > self.table.rowCount()-1:
                self.table.insertRow(self.table.rowCount())
            col = 0
            self.table.setItem(row, col, QTableWidgetItem(ztrace_name))
            col += 1
            s = self.series.data.getZtraceStart(ztrace_name)
            self.table.setItem(row, col, QTableWidgetItem(
                str(s)
            ))
            col += 1
            e = self.series.data.getZtraceEnd(ztrace_name)
            self.table.setItem(row, col, QTableWidgetItem(
                str(e)
            ))
            col += 1
            d = self.series.data.getZtraceDist(ztrace_name)
            self.table.setItem(row, col, QTableWidgetItem(
                str(round(d, 5))
            ))
            col += 1
            g = self.series.ztrace_groups.getObjectGroups(ztrace_name)
            g = ", ".join(g)
            self.table.setItem(row, col, QTableWidgetItem(g))
            col += 1
            self.table.setItem(row, col, QTableWidgetItem(self.series.getAttr(ztrace_name, "alignment", ztrace=True)))

            if resize:
                self.table.resizeColumnsToContents()
                self.table.resizeRowToContents(row)
    
    def createMenus(self):
        """Create the menu for the trace table widget."""
        # Create menubar menu
        menubar_list = [
            {
                "attr_name": "listmenu",
                "text": "List",
                "opts":
                [
                    ("refresh_act", "Refresh", "", self.refresh),
                    ("export_act", "Export...", "", self.export),
                ]
            },
            {
                "attr_name": "filtermenu",
                "text": "Filter",
                "opts":
                [
                    ("refilter_act", "Regex filter...", "", self.setREFilter),
                    ("groupfilter_act", "Group filter...", "", self.setGroupFilter)
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
            ("editname_act", "Edit attributes...", "", self.editAttributes),
            ("smooth_act", "Smooth", "", self.smooth),
            None,
            {
                "attr_name": "menu_3D",
                "text": "3D",
                "opts":
                [
                    ("addto3D_act", "Add to scene", "", self.addTo3D),
                    ("remove3D_act", "Remove from scene", "", self.remove3D)
                ]
            },
            {
                "attr_name" : "group_menu",
                "text": "Group",
                "opts":
                [
                    ("addgroup_act", "Add to group...", "", self.addToGroup),
                    ("removegroup_act", "Remove from group...", "", self.removeFromGroup),
                    ("removeallgroups_act", "Remove from all groups", "", self.removeFromAllGroups)
                ]
            },
            ("setalignment_act", "Change ztrace alignment...", "", self.editAlignment),
            None,
            ("copy_act", "Copy", "", self.table.copy),
            None,
            ("delete_act", "Delete", "", self.delete)
        ]
        self.context_menu = QMenu(self)
        populateMenu(self, self.context_menu, context_menu_list)
            
    def passesFilters(self, name):
        """Determine if an object will be displayed in the table based on existing filters.
        
            Params:
                ztrace_name (str): the name of the ztrace
        """
        # check groups
        filters_len = len(self.group_filters)
        if filters_len != 0:
            groups = self.series.ztrace_groups.getObjectGroups(name)
            groups_len = len(groups)
            union_len = len(groups.union(self.group_filters))
            if union_len == groups_len + filters_len:  # intersection does not exist
                return False
        
        # check regex
        passes_filters = False if self.re_filters else True
        for re_filter in self.re_filters:
            if bool(re.fullmatch(re_filter, name)):
                passes_filters = True
        if not passes_filters:
            return False

        return True

    def updateTitle(self):
        """Update the title of the table."""
        is_regex = tuple(self.re_filters) != (".*",)
        is_group = bool(self.group_filters)

        title = "Ztrace List "
        if any((is_regex, is_group)):
            strs = []
            if is_regex: strs.append("regex")
            if is_group: strs.append("groups")
            title += f"(Filtered by: {', '.join(strs)})"
        
        self.setWindowTitle(title)
    
    def createTable(self):
        """Create the table widget."""
        # close an existing table and save scroll position
        if self.table is not None:
            vscroll = self.table.verticalScrollBar()
            scroll_pos = vscroll.value()
            self.table.close()
        else:
            scroll_pos = 0
        
        # establish table headers
        self.horizontal_headers = ["Name", "Start", "End", "Distance", "Groups", "Alignment"]

        self.updateTitle()

        self.table = CopyTableWidget(0, len(self.horizontal_headers))

        # connect table functions
        self.table.contextMenuEvent = self.ztraceContextMenu
        self.table.mouseDoubleClickEvent = self.addTo3D
        self.table.backspace = self.delete
        
        # filter the objects
        filtered_ztrace_list = []
        for name in self.series.ztraces.keys():
            if self.passesFilters(name):
                filtered_ztrace_list.append(name)
        filtered_ztrace_list = sortList(filtered_ztrace_list)

        # format table
        self.table.setWordWrap(False)
        self.table.setShowGrid(False)  # no grid
        self.table.setAlternatingRowColors(True)  # alternate row colors
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # cannot be edited
        self.table.setHorizontalHeaderLabels(self.horizontal_headers)  # titles
        self.table.verticalHeader().hide()  # no veritcal header
        
        # fill in object data
        for r, name in enumerate(filtered_ztrace_list):
            self.setRow(name, r, resize=True)

        # format rows and columns
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

        # set the saved scroll value
        self.table.verticalScrollBar().setValue(scroll_pos)

        # set table as central widget
        self.main_widget.setCentralWidget(self.table)
    
    def updateZtraces(self, ztrace_names : set):
        """Update the specified ztraces."""
        for name in ztrace_names:
            r, is_in_table = self.table.getRowIndex(name)
            if not is_in_table:
                self.table.insertRow(r)
            self.setRow(name, r)
        
        self.mainwindow.checkActions()
    
    def getSelectedName(self):
        """Get the trace item that is selected by the user."""
        selected_indeces = self.table.selectedIndexes()
        if len(selected_indeces) != 1:
            return
        return self.table.item(selected_indeces[0].row(), 0).text()
    
    def getSelectedNames(self):
        """Get the trace items that iare selected by the user."""
        selected_indeces = self.table.selectedIndexes()
        if len(selected_indeces) < 1:
            return
        return [
            self.table.item(i.row(), 0).text() for i in selected_indeces
        ]    
    
    def resizeEvent(self, event):
        """Resize the table when window is resized."""
        super().resizeEvent(event)
        w = event.size().width()
        h = event.size().height()
        self.table.resize(w, h-20)

    # RIGHT CLICK FUNCTIONS

    def ztraceContextMenu(self, event=None):
        """Executed when button is right-clicked: pulls up menu for user to modify objects."""
        if len(self.table.selectedIndexes()) == 0:
            return
        self.context_menu.exec(event.globalPos())

    def editAttributes(self):
        """Edit the name of a ztrace."""
        names = self.getSelectedNames()
        if names is None:
            return
        if len(names) > 1:
            notify("Please modify one ztrace at a time.")
            return
        name = names[0]

        if name not in self.series.ztraces:
            return
        ztrace = self.series.ztraces[name]

        structure = [
            ["Name:", ("text", name)],
            ["Color:", ("color", ztrace.color)]
        ]
        response, confirmed = QuickDialog.get(self, structure, "Set Attributes")
        if not confirmed:
            return

        new_name, new_color = response

        if new_name != name and new_name in self.series.ztraces:
            notify("This ztrace already exists.")
            return
        
        # keep track of scroll bar position
        vscroll = self.table.verticalScrollBar()
        scroll_pos = vscroll.value()

        self.manager.editAttributes(name, new_name, new_color)
        
        # reset scroll bar position
        vscroll.setValue(scroll_pos)
    
    def smooth(self):
        """Smooth a set of ztraces."""
        names = self.getSelectedNames()
        if not names:
            return

        structure = [
            ["Smoothing factor:", ("int", 10)],
            [("check", ("Create new ztrace", True))]
        ]
        
        response, confirmed = QuickDialog.get(self, structure, "Smooth Ztrace")
        if not confirmed:
            return
        
        smooth = response[0]
        newztrace = response[1][0][1]
        
        self.manager.smooth(names, smooth, newztrace)
    
    def addTo3D(self, event=None):
        """Generate a 3D view of an object"""
        ztrace_names = self.getSelectedNames()
        if ztrace_names:
            self.mainwindow.addTo3D(ztrace_names, ztraces=True)
    
    def remove3D(self):
        """Remove object(s) from the scene."""
        ztrace_names = self.getSelectedNames()
        if ztrace_names:
            self.mainwindow.removeFrom3D(ztrace_names, ztraces=True)
    
    def addToGroup(self, log_event=True):
        """Add objects to a group."""
        ztrace_names = self.getSelectedNames()
        if not ztrace_names:
            return
        
        # ask the user for the group
        group_name, confirmed = ObjectGroupDialog(self, self.series.ztrace_groups).exec()

        if not confirmed:
            return
        
        # save the series state
        self.series_states.addState()
        
        for name in ztrace_names:
            self.series.ztrace_groups.add(group=group_name, obj=name)
            if log_event:
                self.series.addLog(name, None, f"Add to group '{group_name}'")
            self.series.modified_ztraces.add(name)
        
        self.manager.update(clear_tracking=True)
    
    def removeFromGroup(self, log_event=True):
        """Remove objects from a group."""
        ztrace_names = self.getSelectedNames()
        if not ztrace_names:
            return
        
        # ask the user for the group
        group_name, confirmed = ObjectGroupDialog(self, self.series.ztrace_groups, new_group=False).exec()

        if not confirmed:
            return
        
        # save the series state
        self.series_states.addState()
        
        for name in ztrace_names:
            self.series.ztrace_groups.remove(group=group_name, obj=name)
            if log_event:
                self.series.addLog(name, None, f"Remove from group '{group_name}'")
            self.series.modified_ztraces.add(name)
        
        self.manager.update(clear_tracking=True)
    
    def removeFromAllGroups(self, log_event=True):
        """Remove a set of traces from all groups."""
        ztrace_names = self.getSelectedNames()
        if not ztrace_names:
            return
        
        # save the series state
        self.series_states.addState()
        
        for name in ztrace_names:
            self.series.ztrace_groups.removeObject(name)
            if log_event:
                self.series.addLog(name, None, f"Remove from all object groups")
            self.series.modified_ztraces.add(name)
            
        self.manager.update(clear_tracking=True)
    
    def editAlignment(self):
        """Edit alignment for ztrace(s)."""
        names = self.getSelectedNames()
        if not names:
            notify("Please select at least one ztrace.")
            return
        
        structure = [
            ["Alignment:", ("combo", ["no-alignment"] + list(self.mainwindow.field.section.tforms.keys()))]
        ]
        response, confirmed = QuickDialog.get(self, structure, "Object Alignment")
        if not confirmed:
            return
        
        # save the series state
        self.series_states.addState()
        
        alignment = response[0]
        if not alignment: alignment = None
        for name in names:
            self.series.setAttr(name, "alignment", alignment, ztrace=True)
            self.series.addLog(name, None, "Edit default alignment")
        
        self.refresh()
    
    def delete(self):
        """Delete a set of ztraces."""
        names = self.getSelectedNames()
        if not names:
            return
        
        self.manager.delete(names)

    # MENU-RELATED FUNCTIONS

    def refresh(self):
        """Refresh the tables."""
        self.manager.refresh()
    
    def export(self):
        """Export the trace list as a csv file."""
        # get the location from the user
        file_path = FileDialog.get(
            "save",
            self,
            "Save Ztrace List",
            file_name="ztraces.csv",
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
    
    def closeEvent(self, event):
        """Remove self from manager table list."""
        self.manager.tables.remove(self)
        super().closeEvent(event)
