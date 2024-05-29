import re

from PySide6.QtWidgets import (
    QTableWidgetItem, 
    QWidget, 
    QMenu, 
)

from .data_table import DataTable
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
)

class ZtraceTableWidget(DataTable):

    def __init__(self, series : Series, mainwindow : QWidget, manager):
        """Create the object table dock widget.
        
            Params:
                series (Series): the series object
                mainwindow (QWidget): the main window the dock is connected to
                manager: the object table manager
        """
        self.re_filters = set([".*"])
        self.group_filters = set()

        super().__init__("ztrace", series, mainwindow, manager)
        self.static_columns = ["Name"]
        self.createTable()

        self.show()
    
    def getItems(self, ztrace_name : str, item_type : str):
        """"""
        items = []

        if item_type == "Name":
            items.append(QTableWidgetItem(ztrace_name))
        elif item_type == "Start":
            s = self.series.data.getZtraceStart(ztrace_name)
            items.append(QTableWidgetItem(
                str(s)
            ))
        elif item_type == "End":
            e = self.series.data.getZtraceEnd(ztrace_name)
            items.append(QTableWidgetItem(
                str(e)
            ))
        elif item_type == "Distance":
            d = self.series.data.getZtraceDist(ztrace_name)
            items.append(QTableWidgetItem(
                str(round(d, 5))
            ))
        elif item_type == "Groups":
            g = self.series.ztrace_groups.getObjectGroups(ztrace_name)
            g = ", ".join(g)
            items.append(QTableWidgetItem(g))
        elif item_type == "Alignment":
            items.append(QTableWidgetItem(self.series.getAttr(ztrace_name, "alignment", ztrace=True)))
        
        return items
    
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
            super().setRow(ztrace_name, row, resize)
    
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
                    ("setcolumns_act", "Set columns...", "", self.setColumns),
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
        self.menubar.clear()
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
            
    def passesFilters(self, name : str):
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
    
    def getFiltered(self):
        """Get the list of filtered ztraces."""
        ztrace_names = sortList(list(self.series.ztraces.keys()))
        passing = []
        
        for n in ztrace_names:
            if self.passesFilters(n):
                passing.append(n)
        
        return passing

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
    
    def updateData(self, ztrace_names : set):
        """Update the specified ztraces."""
        for name in ztrace_names:
            r, is_in_table = self.table.getRowIndex(name)
            if not is_in_table:
                self.table.insertRow(r)
            self.setRow(name, r)
        
        self.mainwindow.checkActions()
    
    def getSelected(self, single=False):
        """Get the trace items that iare selected by the user."""
        selected_indeces = self.table.selectedIndexes()
        if len(selected_indeces) < 1:
            return
        selected = [
            self.table.item(i.row(), 0).text() for i in selected_indeces
        ]

        if single:
            if len(selected) != 1:
                notify("Please select only one ztrace for this option.")
                return
            else:
                return selected[0]
        else:
            return selected

    # RIGHT CLICK FUNCTIONS

    def editAttributes(self):
        """Edit the name of a ztrace."""
        names = self.getSelected()
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
        names = self.getSelected()
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
        ztrace_names = self.getSelected()
        if ztrace_names:
            self.mainwindow.addTo3D(ztrace_names, ztraces=True)
    
    def remove3D(self):
        """Remove object(s) from the scene."""
        ztrace_names = self.getSelected()
        if ztrace_names:
            self.mainwindow.removeFrom3D(ztrace_names, ztraces=True)
    
    def addToGroup(self, log_event=True):
        """Add objects to a group."""
        ztrace_names = self.getSelected()
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
        ztrace_names = self.getSelected()
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
        ztrace_names = self.getSelected()
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
        names = self.getSelected()
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
        names = self.getSelected()
        if not names:
            return
        
        self.manager.delete(names)
    
    def backspace(self):
        """Called when backspace is pressed."""
        self.delete()

    # MENU-RELATED FUNCTIONS   
    
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
