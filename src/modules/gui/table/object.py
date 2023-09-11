import re
import os
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, 
    QDockWidget, 
    QTableWidgetItem,  
    QWidget, 
    QInputDialog, 
    QMenu, 
    QFileDialog,
)
from PySide6.QtCore import Qt

from .copy_table_widget import CopyTableWidget
from .history import HistoryTableWidget

from modules.datatypes import Series
from modules.gui.utils import (
    populateMenuBar,
    populateMenu,
    noUndoWarning
)
from modules.gui.dialog import (
    ObjectGroupDialog,
    TableColumnsDialog,
    Object3DDialog,
    TraceDialog,
    ShapesDialog,
    CurateFiltersDialog
)
from modules.constants import fd_dir

def getDateTime():
    dt = datetime.now()
    d = f"{dt.year % 1000}-{dt.month:02d}-{dt.day:02d}"
    t = f"{dt.hour:02d}:{dt.minute:02d}"
    return d, t

class ObjectTableWidget(QDockWidget):

    def __init__(self, series : Series, mainwindow : QWidget, manager):
        """Create the object table dock widget.
        
            Params:
                series (Series): the Series object
                mainwindow (MainWindow): the main window the dock is connected to
                manager: the object table manager
        """
        # initialize the widget
        super().__init__(mainwindow)
        self.series = series
        self.mainwindow = mainwindow

        # set desired format for widget
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)  # can be docked to right or left side
        self.setWindowTitle("Object List")

        # set defaults
        self.columns = {
            "Range" : True,
            "Count" : False,
            "Flat area" : False,
            "Volume": False,
            "Groups": True,
            "Trace tags": False,
            "Last user": True,
            "Curate": False
        }
        self.re_filters = set([".*"])
        self.tag_filters = set()
        self.group_filters = set()
        self.cr_status_filter = {
            "Blank": True,
            "Needs curation": True,
            "Curated": True
        }
        self.cr_user_filters = set()

        # create the main window widget
        self.main_widget = QMainWindow()
        self.setWidget(self.main_widget)
        
        # create the table and the menu
        self.table = None
        self.process_check_event = False
        self.createTable()
        self.createMenus()

        # save manager object
        self.manager = manager

        self.show()
    
    def createMenus(self):
        """Create the menu for the object table widget."""
        # Create menubar menu
        menubar_list = [
            {
                "attr_name": "listmenu",
                "text": "List",
                "opts":
                [
                    ("refresh_act", "Refresh", "", self.refresh),
                    ("columns_act", "Set columns...", "", self.setColumns),
                    ("export_act", "Export...", "", self.export),
                    {
                        "attr_name": "filtermenu",
                        "text": "Filter",
                        "opts":
                        [
                            ("refilter_act", "Regex filter...", "", self.setREFilter),
                            ("groupfilter_act", "Group filter...", "", self.setGroupFilter),
                            ("tagfilter_act", "Tag filter...", "", self.setTagFilter),
                            ("crstatusfilter_act", "Curation filter...", "", self.setCRFilter)
                        ]
                    }
                ]
            },

            {
                "attr_name": "findmenu",
                "text": "Find",
                "opts":
                [
                    ("findfirst_act", "First", "", self.findFirst),
                    ("findlast_act", "Last", "", self.findLast)
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
            ("editattribtues_act", "Edit attributes...", "", self.editAttributes),
            {
                "attr_name": "stampmenu",
                "text": "Stamp attributes",
                "opts":
                [
                    ("editradius_act", "Edit radius...", "", self.editRadius),
                    ("editshape_act", "Edit shape...", "", self.editShape)
                ]
            },
            ("removealltags_act", "Remove all tags", "", self.removeAllTags),
            None,
            ("hideobj_act", "Hide", "", self.hideObj),
            ("unhideobj_act", "Unhide", "", lambda : self.hideObj(False)),
            None,
            {
                "attr_name": "curatemenu",
                "text": "Set curation",
                "opts":
                [
                    ("blankcurate_act", "Blank", "", lambda : self.bulkCurate("")),
                    ("needscuration_act", "Needs curation", "", lambda : self.bulkCurate("Needs curation")),
                    ("curated_act", "Curated", "", lambda : self.bulkCurate("Curated"))
                ]
            },
            None,
            {
                "attr_name": "menu_3D",
                "text": "3D",
                "opts":
                [
                    ("addto3D_act", "Add to scene", "", self.addTo3D),
                    ("remove3D_act", "Remove from scene", "", self.remove3D),
                    None,
                    ("edit3D_act", "Edit 3D settings...", "", self.edit3D)
                ]
            },
            None,
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
            None,
            ("history_act", "View history", "", self.viewHistory),
            None,
            {
                "attr_name": "ztrace_menu",
                "text": "Create ztrace",
                "opts":
                [
                    ("csztrace_act", "On contour midpoints", "", self.createZtrace),
                    ("atztrace_act", "From trace sequence", "", lambda : self.createZtrace(cross_sectioned=False)),
                ]
            },
            None,
            ("copy_act", "Copy", "", self.table.copy),
            None,
            ("delete_act", "Delete", "", self.deleteObjects)
        ]
        self.context_menu = QMenu(self)
        populateMenu(self, self.context_menu, context_menu_list)
    
    def setRow(self, name : str, row : int, resize_columns=True):
        """Set the data for a row of the table.
        
            Params:
                name (str): the name of the object
                row (int): the row to enter this data into
        """
        self.process_check_event = False
        self.table.setItem(row, 0, QTableWidgetItem(name))
        col = 1
        if self.columns["Range"]:
            self.table.setItem(row, col, QTableWidgetItem(str(self.series.data.getStart(name))))
            col += 1
            self.table.setItem(row, col, QTableWidgetItem(str(self.series.data.getEnd(name))))
            col += 1
        if self.columns["Count"]:
            self.table.setItem(row, col, QTableWidgetItem(str(self.series.data.getCount(name))))
            col += 1
        if self.columns["Flat area"]:
            self.table.setItem(row, col, QTableWidgetItem(str(round(self.series.data.getFlatArea(name), 5))))
            col += 1
        if self.columns["Volume"]:
            self.table.setItem(row, col, QTableWidgetItem(str(round(self.series.data.getVolume(name), 5))))
            col += 1
        if self.columns["Groups"]:
            groups = self.series.object_groups.getObjectGroups(name)
            groups_str = ", ".join(groups)
            self.table.setItem(row, col, QTableWidgetItem(groups_str))
            col += 1
        if self.columns["Trace tags"]:
            tags = self.series.data.getTags(name)
            tags_str = ", ".join(tags)
            self.table.setItem(row, col, QTableWidgetItem(tags_str))
            col += 1
        if self.columns["Last user"]:
            if name in self.series.last_user:
                last_user = self.series.last_user[name]
            else:
                last_user = ""
            self.table.setItem(row, col, QTableWidgetItem(last_user))
            col += 1
        if self.columns["Curate"]:
            check_item = QTableWidgetItem("")
            status_item = QTableWidgetItem("")
            user_item = QTableWidgetItem("")
            date_item = QTableWidgetItem("")
            cr_items = [check_item, status_item, user_item, date_item]
            check_item.setFlags(Qt.ItemFlag.ItemIsUserTristate | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)

            if name not in self.series.curation:
                check_item.setCheckState(Qt.CheckState.Unchecked)
                cr_color = None
            else:
                curated, user, date = self.series.curation[name]
                if curated:
                    check_item.setCheckState(Qt.CheckState.Checked)
                    status_item.setText("Curated")
                    cr_color = Qt.cyan
                else:
                    check_item.setCheckState(Qt.CheckState.PartiallyChecked)
                    status_item.setText(f"Needs curation")
                    cr_color = Qt.yellow
                user_item.setText(user)
                date_item.setText(date)
            
            for item in cr_items:
                if cr_color:
                    item.setBackground(cr_color)
                self.table.setItem(row, col, item)
                col += 1
        # self.table.resizeRowToContents(row)
        if resize_columns:
            self.table.resizeColumnsToContents()
        self.process_check_event = True
    
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
        
        # check curation status and user
        if self.columns["Curate"]:
            if name in self.series.curation:
                cr_status, user, date = self.series.curation[name]
                cr_status = "Curated" if cr_status else "Needs curation"
                if not self.cr_status_filter[cr_status]:
                    return False
                if self.cr_user_filters and user not in self.cr_user_filters:
                    return False          
            else:
                if not self.cr_status_filter["Blank"]:
                    return False
                if self.cr_user_filters:
                    return False
        
        # check regex
        for re_filter in self.re_filters:
            if not bool(re.fullmatch(re_filter, name)):
                return False
        
        return True

    def getFilteredObjects(self):
        """Get the names of the objects that pass the filter."""
        filtered_object_list = []
        for name in self.series.data["objects"]:
            if self.passesFilters(name):
                filtered_object_list.append(name)
        
        return sorted(filtered_object_list)

    def createTable(self):
        """Create the table widget.
        
            Params:
                objdata (dict): the dictionary containing the object table data objects
        """
        # close an existing table if one exists
        if self.table is not None:
            self.table.close()

        # establish table headers
        self.curate_column = None
        self.horizontal_headers = ["Name"]
        for key, b in self.columns.items():
            if b and key == "Range":
                self.horizontal_headers.append("Start")
                self.horizontal_headers.append("End")
            elif b and key == "Curate":
                self.curate_column = len(self.horizontal_headers)
                self.horizontal_headers.append("CR")
                self.horizontal_headers.append("Status")
                self.horizontal_headers.append("User")
                self.horizontal_headers.append("Date")
            elif b:
                self.horizontal_headers.append(key)
        
        # filter the objects
        filtered_obj_names = self.getFilteredObjects()

        # create the table object
        self.table = CopyTableWidget(len(filtered_obj_names), len(self.horizontal_headers), self.main_widget)

        # connect table functions
        self.table.mouseDoubleClickEvent = self.findFirst
        self.table.contextMenuEvent = self.objectContextMenu
        self.table.itemChanged.connect(self.checkCurate)

        # format table
        # self.table.setWordWrap(False)
        self.table.setShowGrid(False)  # no grid
        self.table.setAlternatingRowColors(True)  # alternate row colors
        # self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # cannot be edited
        self.table.setHorizontalHeaderLabels(self.horizontal_headers)  # titles
        self.table.verticalHeader().hide()  # no veritcal header
        
        # fill in object data
        for r, n in enumerate(filtered_obj_names):
            self.setRow(n, r, resize_columns=False)

        # format rows and columns
        self.table.resizeRowsToContents()
        for c in range(self.table.columnCount()):
            header = self.table.horizontalHeaderItem(c)
            if not (header == "Name" or header == "Groups"):
                self.table.resizeColumnToContents(c)

        # set table as central widget
        self.main_widget.setCentralWidget(self.table)

    def getRowIndex(self, obj_name : str):
        """Get the row index of an object in the table (or where it SHOULD be on the table).
        
            Parmas:
                obj_name (str): the name of the object
            Returns:
                (int): the row index for that object in the table
                (bool): whether or not the object actually exists in the table
        """
        for row_index in range(self.table.rowCount()):
            row_name = self.table.item(row_index, 0).text()
            if obj_name == row_name:
                return row_index, True
            elif obj_name < row_name:
                return row_index, False
        return self.table.rowCount(), False
    
    def updateObjects(self, names):
        """Update the data for a set of objects.
        
            Params:
                names (iterable): the names of the objects to update
        """
        for name in names:
            # check if object passes filters
            if not self.passesFilters(name):
                # special case: does not pass filter anymore but exists on table
                row, exists_in_table = self.getRowIndex(name)
                if exists_in_table:
                    self.table.removeRow(row)
                return

            # update if it does
            row, exists_in_table = self.getRowIndex(name)
            if exists_in_table and name not in self.series.data["objects"]:  # completely delete object
                self.table.removeRow(row)
            elif exists_in_table and name in self.series.data["objects"]:  # update existing object
                self.setRow(name, row)
            elif not exists_in_table and name in self.series.data["objects"]:  # add new object
                self.table.insertRow(row)
                self.setRow(name, row)
    
    def resizeEvent(self, event):
        """Resize the table when window is resized."""
        super().resizeEvent(event)
        w = event.size().width()
        h = event.size().height()
        self.table.resize(w, h-20)
    
    def getSelectedObject(self) -> str:
        """Get the name of the object highlighted by the user.
        
            Returns:
                (str): the name of the object
        """
        selected_indexes = self.table.selectedIndexes()
        if len(selected_indexes) != 1:
            return None
        r = selected_indexes[0].row()
        obj_name = self.table.item(r, 0).text()
        return obj_name
    
    def getSelectedObjects(self) -> list[str]:
        """Get the name of the objects highlighted by the user.
        
            Returns:
                (list): the name of the objects
        """
        selected_indexes = self.table.selectedIndexes()
        obj_names = []
        for i in selected_indexes:
            r = i.row()
            obj_names.append(self.table.item(r, 0).text())
        return obj_names

    def checkCurate(self, item : QTableWidgetItem):
        """User checked a curate checkbox."""
        # check for curation
        if (not self.process_check_event or 
            self.curate_column is None or 
            item.column() != self.curate_column):
            return

        r = item.row()
        c = item.column()
        name = self.table.item(r, 0).text()
        state = item.checkState()
        if state == Qt.CheckState.Unchecked:
            self.series.setCuration([name], "")
        elif state == Qt.CheckState.PartiallyChecked:
            assign_to, confirmed = QInputDialog.getText(
                self,
                "Assign to",
                "Assign curation to username:\n(press enter to leave blank)" 
            )
            if not confirmed:
                item.setCheckState(Qt.CheckState.Unchecked)
                return
            self.series.setCuration([name], "Needs curation", assign_to)
        elif state == Qt.CheckState.Checked:
            self.series.setCuration([name], "Curated")
        self.setRow(name, r)
        self.table.resizeColumnToContents(c + 1)
        self.table.resizeColumnToContents(c + 2)
        self.table.resizeColumnToContents(c + 3)

        self.table.resizeColumnToContents(self.curate_column)
        # self.table.resizeRowToContents(r)

        self.manager.updateObjects([name])

        self.mainwindow.seriesModified(True)

    # RIGHT CLICK FUNCTIONS

    def objectContextMenu(self, event=None):
        """Executed when button is right-clicked: pulls up menu for user to modify objects."""
        if len(self.table.selectedIndexes()) == 0:
            return
        self.context_menu.exec(event.globalPos())   
    
    def editAttributes(self):
        """Edit the name of an object in the entire series."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return

        # ask the user for the new object name
        if len(obj_names) == 1:
            displayed_name = obj_names[0]
            tags = self.series.data.getTags(obj_names[0])
        else:
            displayed_name = None
            tags=None
        
        attr_trace, confirmed = TraceDialog(self, name=displayed_name, tags=tags).exec()

        if not confirmed:
            return
        
        # confirm with user
        if not noUndoWarning():
            return
        
        self.manager.editAttributes(obj_names, attr_trace)
    
    def editRadius(self):
        """Modify the radius of the trace on an entire object."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return
        
        new_rad, confirmed = QInputDialog.getText(
            self, 
            "Object Trace Radius",
            "Enter the new radius:",
        )
        if not confirmed:
            return

        try:
            new_rad = float(new_rad)
        except ValueError:
            return
        
        if new_rad == 0:
            return
        
        if not noUndoWarning():
            return
        
        self.manager.editRadius(obj_names, new_rad)
    
    def editShape(self):
        """Modify the shape of the traces on an entire object."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return
        
        new_shape, confirmed = ShapesDialog(self).exec()
        if not confirmed:
            return
        
        if not noUndoWarning():
            return
        
        self.manager.editShape(obj_names, new_shape)
    
    def hideObj(self, hide=True):
        """Edit whether or not an object is hidden in the entire series.
        
            Params:
                hide (bool): True if the object should be hidden
        """
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return
        
        self.manager.hideObjects(obj_names, hide)

    def addTo3D(self):
        """Generate a 3D view of an object"""
        obj_names = self.getSelectedObjects()
        if obj_names:
            self.mainwindow.addTo3D(obj_names)
    
    def remove3D(self):
        """Remove object(s) from the scene."""
        obj_names = self.getSelectedObjects()
        if obj_names:
            self.mainwindow.removeFrom3D(obj_names)

    def addToGroup(self, log_event=True):
        """Add objects to a group."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return
        
        # ask the user for the group
        group_name, confirmed = ObjectGroupDialog(self, self.series.object_groups).exec()

        if not confirmed:
            return
        
        for name in obj_names:
            self.series.object_groups.add(group=group_name, obj=name)
            if log_event:
                self.series.addLog(name, None, f"Add to group '{group_name}'")
        
        self.manager.updateObjects(obj_names)

    
    def removeFromGroup(self, log_event=True):
        """Remove objects from a group."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return
        
        # ask the user for the group
        group_name, confirmed = ObjectGroupDialog(self, self.series.object_groups, new_group=False).exec()

        if not confirmed:
            return
        
        for name in obj_names:
            self.series.object_groups.remove(group=group_name, obj=name)
            if log_event:
                self.series.addLog(name, None, f"Remove from group '{group_name}'")
        
        self.manager.updateObjects(obj_names)
    
    def removeFromAllGroups(self, log_event=True):
        """Remove a set of traces from all groups."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return
        
        for name in obj_names:
            self.series.object_groups.removeObject(name)
            if log_event:
                self.series.addLog(name, None, f"Remove from all object groups")
            
        self.manager.updateObjects(obj_names)
    
    def removeAllTags(self):
        """Remove all tags from all traces on selected objects."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return

        # confirm with user
        if not noUndoWarning():
            return
        
        self.manager.removeAllTraceTags(obj_names)
    
    def viewHistory(self):
        """View the history for a set of objects."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return
        
        HistoryTableWidget(self.series.getFullHistory(), self.mainwindow, obj_names)
    
    def createZtrace(self, cross_sectioned=True):
        """Create a ztrace from selected objects."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return
        self.manager.createZtrace(obj_names, cross_sectioned)

    def deleteObjects(self):
        """Delete an object from the entire series."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return
        
        if not noUndoWarning():
            return
        
        self.manager.deleteObjects(obj_names) 

    # MENU-RELATED FUNCTIONS

    def refresh(self):
        """Refresh the object lists."""
        self.manager.refresh()
    
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
        """Export the object list as a csv file."""
        # get the location from the user
        global fd_dir
        file_path, ext = QFileDialog.getSaveFileName(
            self,
            "Save Object List",
            os.path.join(fd_dir.get(), "objects.csv"),
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
        # object data
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
            "Filter Objects",
            "Enter the object filters:",
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
            "Filter Objects",
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
            "Filter Objects",
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
    
    def setCRFilter(self):
        """Set the filter for curation."""
        response, confirmed = CurateFiltersDialog(
            self, 
            self.cr_status_filter, 
            self.cr_user_filters
        ).exec()
        if not confirmed:
            return
        
        self.cr_status_filter, self.cr_user_filters = response

        # call through manager to update self
        self.manager.updateTable(self)
    
    def findFirst(self, event=None):
        """Focus the field on the first occurence of an object in the series."""
        obj_name = self.getSelectedObject()
        if obj_name is None:
            return
        self.manager.findObject(obj_name, first=True)
    
    def findLast(self):
        """Focus the field on the last occurence of an object in the series."""
        obj_name = self.getSelectedObject()
        if obj_name is None:
            return
        self.manager.findObject(obj_name, first=False)
    
    def edit3D(self):
        """Edit the 3D options for an object or set of objects."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return
        
        # check for object names and opacities
        if obj_names[0] in self.series.object_3D_modes:
            type_3D, opacity = self.series.object_3D_modes[obj_names[0]]
        else:
            type_3D, opacity= "surface", 1
        for name in obj_names[1:]:
            if name in self.series.object_3D_modes:
                new_type, new_opacity = self.series.object_3D_modes[name]
            else:
                new_type, new_opacity = "surface", 1
            if type_3D != new_type:
                type_3D = None
            if opacity != new_opacity:
                opacity = None

        settings, confirmed = Object3DDialog(
            self,
            type3D=type_3D,
            opacity=opacity
        ).exec()
        if not confirmed:
            return
        
        new_type, new_opacity = settings

        self.manager.edit3D(obj_names, new_type, new_opacity)
    
    def bulkCurate(self, curation_status : str):
        """Set the curation status for multiple selected objects.
        
            Params:
                curation_status (str): "", "Needs curation" or "Curated"
        """
        names = self.getSelectedObjects()
        if not names:
            return
        
        # prompt assign to
        if curation_status == "Needs curation":
            assign_to, confirmed = QInputDialog.getText(
                self,
                "Assign to",
                "Assign curation to username:\n(press enter to leave blank)"
            )
            if not confirmed:
                return
        else:
            assign_to = ""
        
        self.series.setCuration(names, curation_status, assign_to)
        self.manager.updateObjects(names)
        self.mainwindow.seriesModified(True)
    
    def closeEvent(self, event):
        """Remove self from manager table list."""
        self.manager.tables.remove(self)
        super().closeEvent(event)

