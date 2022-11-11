import re

from PySide6.QtWidgets import QMainWindow, QDockWidget, QTableWidget, QTableWidgetItem, QAbstractItemView, QWidget, QInputDialog, QMenu, QFileDialog, QColorDialog
from PySide6.QtCore import Qt

from modules.pyrecon.series import Series

from modules.backend.object_table_item import ObjectTableItem
from modules.backend.gui_functions import populateMenuBar, populateMenu

from modules.gui.dialog import ObjectGroupDialog, ObjectTableColumnsDialog

class ObjectTableWidget(QDockWidget):

    def __init__(self, series : Series, objdict : dict, parent : QWidget, manager):
        """Create the object table dock widget.
        
            Params:
                series (Series): the Series object
                objdict (dict): contains all object info for the table
                parent (QWidget): the main window the dock is connected to
                manager: the object table manager
        """
        # initialize the widget
        super().__init__(parent)
        self.series = series
        self.parent_widget = parent

        # set desired format for widget
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)  # ccan be docked to right or left side
        self.setWindowTitle("Object List")

        # set defaults
        self.columns = {
            "Range" : True,
            "Count" : True,
            "Flat area" : True,
            "Volume": True,
            "Groups": True,
            "Trace tags": False
        }
        self.re_filters = set([".*"])
        self.tag_filters = set()
        self.group_filters = set()

        # create the main window widget
        self.main_widget = QMainWindow()
        self.setWidget(self.main_widget)
        
        # create the table and the menu
        self.table = None
        self.createTable(objdict)
        self.createMenus()

        # set geometry
        w = 20
        for i in range(self.table.columnCount()):
            w += self.table.columnWidth(i)
        h = self.parent_widget.height() - 90
        x = self.parent_widget.x() + 10
        y = self.parent_widget.y() + 90
        #self.setGeometry(x, y, w, h)

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
                            ("groupfilter_act", "Group fiter...", "", self.setGroupFilter),
                            ("tagfilter_act", "Tag filter...", "", self.setTagFilter)
                        ]
                    }
                ]
            },

            {
                "attr_name": "findmenu",
                "text": "Find",
                "opts":
                [
                    ("findfirst_act", "First trace", "", self.findFirst),
                    ("findlast_act", "Last trace", "", self.findLast)
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
            ("editobjname_act", "Edit name...", "", self.editObjName),
            ("editobjcolor_act", "Edit color...", "", self.editObjColor),
            ("generate3D_act", "Generate 3D", "", self.generate3D),
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
            {
                "attr_name" : "tag_menu",
                "text": "Tags",
                "opts":
                [
                    ("addtag_act", "Add tag...", "", self.addTag),
                    ("removetag_act", "Remove tag...", "", self.removeTag),
                    ("removealltags_act", "Remove all tags", "", self.removeAllTags)
                ]
            },
            ("delete_act", "Delete", "", self.deleteObjects)
        ]
        self.context_menu = QMenu(self)
        populateMenu(self, self.context_menu, context_menu_list)
    
    def setRow(self, obj_data : ObjectTableItem, row : int):
        """Set the data for a row of the table.
        
            Params:
                object_data (ObjectTableItem): the object containing the data for the object
                row (int): the row to enter this data into
        """
        self.table.setItem(row, 0, QTableWidgetItem(obj_data.name))
        col = 1
        if self.columns["Range"]:
            self.table.setItem(row, col, QTableWidgetItem(str(obj_data.getStart())))
            col += 1
            self.table.setItem(row, col, QTableWidgetItem(str(obj_data.getEnd())))
            col += 1
        if self.columns["Count"]:
            self.table.setItem(row, col, QTableWidgetItem(str(obj_data.getCount())))
            col += 1
        if self.columns["Flat area"]:
            self.table.setItem(row, col, QTableWidgetItem(str(round(obj_data.getFlatArea(), 5))))
            col += 1
        if self.columns["Volume"]:
            self.table.setItem(row, col, QTableWidgetItem(str(round(obj_data.getVolume(), 5))))
            col += 1
        if self.columns["Groups"]:
            groups = self.series.object_groups.getObjectGroups(obj_data.name)
            groups_str = ", ".join(groups)
            self.table.setItem(row, col, QTableWidgetItem(groups_str))
            col += 1
        if self.columns["Trace tags"]:
            tags = obj_data.getTags()
            tags_str = ", ".join(tags)
            self.table.setItem(row, col, QTableWidgetItem(tags_str))
            col += 1
            
    def passesFilters(self, item : ObjectTableItem):
        """Determine if an object will be displayed in the table based on existing filters.
        
            Params:
                item (ObjectTableItem): the item containing the data
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
            object_tags = item.getTags()
            object_len = len(object_tags)
            union_len = len(object_tags.union(self.tag_filters))
            if union_len == object_len + filters_len:  # intersection does not exist
                return False
        
        # check regex (will only be run if passes tags)
        for re_filter in self.re_filters:
            if bool(re.fullmatch(re_filter, item.name)):
                return True
        return False
    
    def createTable(self, objdict : dict):
        """Create the table widget.
        
            Params:
                objdata (dict): the dictionary containing the object table data objects
        """
        # close an existing table if one exists
        if self.table is not None:
            self.table.close()

        # establish table headers
        self.horizontal_headers = ["Name"]
        if self.columns["Range"]:
            self.horizontal_headers.append("Start")
            self.horizontal_headers.append("End")
        if self.columns["Count"]:
            self.horizontal_headers.append("Count")
        if self.columns["Flat area"]:
            self.horizontal_headers.append("Flat Area")
        if self.columns["Volume"]:
            self.horizontal_headers.append("Volume")
        if self.columns["Groups"]:
            self.horizontal_headers.append("Groups")
        if self.columns["Trace tags"]:
            self.horizontal_headers.append("Trace Tags")
        
        # filter the objects
        sorted_obj_names = sorted(list(objdict.keys()))
        filtered_obj_names = []
        for name in sorted_obj_names:
            if self.passesFilters(objdict[name]):
                filtered_obj_names.append(name)

        # create the table object
        self.table = QTableWidget(len(filtered_obj_names), len(self.horizontal_headers), self.main_widget)

        # connect table functions
        self.table.mouseDoubleClickEvent = self.generate3D
        self.table.contextMenuEvent = self.objectContextMenu

        # format table
        # self.table.setWordWrap(False)
        self.table.setShowGrid(False)  # no grid
        self.table.setAlternatingRowColors(True)  # alternate row colors
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # cannot be edited
        self.table.setHorizontalHeaderLabels(self.horizontal_headers)  # titles
        self.table.verticalHeader().hide()  # no veritcal header
        
        # fill in object data
        for r, n in enumerate(filtered_obj_names):
            self.setRow(objdict[n], r)

        # format rows and columns
        self.table.resizeRowsToContents()
        for c in range(self.table.columnCount()):
            header = self.horizontal_headers[c]
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
        return self.table.rowCount() + 1, False
    
    def updateObject(self, objdata : ObjectTableItem):
        """Update the data for a specific object.
        
            Params:
                objdata (ObjectTableItem): the object containing the table data
        """
        # check if object passes filters
        if not self.passesFilters(objdata):
            # special case: does not pass filter anymore but exists on table
            row, exists_in_table = self.getRowIndex(objdata.name)
            if exists_in_table:
                self.table.removeRow(row)
            return

        # update if it does
        row, exists_in_table = self.getRowIndex(objdata.name)
        if exists_in_table and objdata.isEmpty():  # completely delete object
            self.table.removeRow(row)
        elif exists_in_table and not objdata.isEmpty():  # update existing object
            self.setRow(objdata, row)
        elif not exists_in_table and not objdata.isEmpty():  # add new object
            self.table.insertRow(row)
            self.setRow(objdata, row)
    
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

    # RIGHT CLICK FUNCTIONS

    def objectContextMenu(self, event=None):
        """Executed when button is right-clicked: pulls up menu for user to modify objects.
        
            Params:
                event: contains user input data (location of right click)
        """
        if len(self.table.selectedIndexes()) == 0:
            return
        self.context_menu.exec(event.globalPos())   
    
    def editObjName(self):
        """Edit the name of an object in the entire series."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return

        # ask the user for the new object name
        if len(obj_names) == 1:
            displayed_name = obj_names[0]
        else:
            displayed_name = ""
        name, confirmed = QInputDialog.getText(
            self,
            "New Object Name",
            "Enter the new name for the object:",
            text=displayed_name
        )
        if not confirmed:
            return
        
        self.manager.modifyObjects(obj_names, name=name)
    
    def editObjColor(self):
        """Edit the color of an object in the entire series."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return

        # ask the user for the new color
        c = QColorDialog.getColor()
        color = (c.red(), c.green(), c.blue())

        if not color:
            return
        
        self.manager.modifyObjects(obj_names, color=color)
    
    def generate3D(self, event=None):
        """Generate a 3D view of an object"""
        obj_names = self.getSelectedObjects()
        if obj_names:
            self.manager.generate3D(obj_names)
    
    def addToGroup(self):
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
            self.manager.refreshObject(name)
    
    def removeFromGroup(self):
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
            self.manager.refreshObject(name)
    
    def removeFromAllGroups(self):
        """Remove a set of traces from all groups."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return
        
        for name in obj_names:
            groups = self.series.object_groups.getObjectGroups(name)
            for group in groups.copy():
                self.series.object_groups.remove(group=group, obj=name)
            self.manager.refreshObject(name)
    
    def addTag(self):
        """Add a tag to all traces on selected objects."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return
        
        tag_name, confirmed = QInputDialog.getText(
            self,
            "Tag Traces",
            "Enter the trace tag:"
        )
        if not confirmed:
            return
        
        self.manager.tagTraces(obj_names, tag_name)
    
    def removeTag(self):
        """Remove a tag from all traces on selected objects."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return
        
        tag_name, confirmed = QInputDialog.getText(
            self,
            "Remove Tag",
            "Enter the tag to remove:"
        )
        if not confirmed:
            return
        
        self.manager.tagTraces(obj_names, tag_name, remove=True)
    
    def removeAllTags(self):
        """Remove all tags from all traces on selected objects."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return
        
        self.manager.removeAllTraceTags(obj_names)

    def deleteObjects(self):
        """Delete an object from the entire series."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return
        self.manager.deleteObjects(obj_names) 

    # MENU-RELATED FUNCTIONS

    def refresh(self):
        """Refresh the object lists."""
        self.manager.refresh()
    
    def setColumns(self):
        """Set the columns to display."""
        new_cols, confirmed = ObjectTableColumnsDialog(
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
        file_path, ext = QFileDialog.getSaveFileName(
            self,
            "Save Object List",
            "objects.csv",
            filter="Comma Separated Values (.csv)"
        )
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
    
    def findFirst(self):
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
