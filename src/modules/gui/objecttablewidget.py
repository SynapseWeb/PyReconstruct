import re

from PySide6.QtWidgets import QMainWindow, QDockWidget, QTableWidget, QTableWidgetItem, QAbstractItemView, QWidget, QInputDialog
from PySide6.QtCore import Qt
from modules.backend.gui_functions import populateMenuBar

from modules.pyrecon.series import Series

from modules.backend.object_table_item import ObjectTableItem

from modules.calc.quantification import sigfigRound

class ObjectTableWidget(QDockWidget):

    def __init__(self, series : Series, objdict : dict, parent : QWidget, manager):
        """Create the object table dock widget.
        
            Params:
                series (Series): the Series object
                quantities (dict): information on which calculations to include
                parent (QWidget): the main window the dock is connected to
        """
        # initialize the widget
        super().__init__(parent)
        self.series = series
        self.parent_widget = parent

        # set desired format for widget
        self.setFloating(True)  # not docked to the window
        self.setAllowedAreas(Qt.NoDockWidgetArea)  # cannot be docked to the window
        self.setWindowTitle("Object List")

        # set defaults
        self.quantities = {
            "range" : True,
            "count" : True,
            "flat_area" : True,
            "volume": True
        }
        self.re_filters = set([".*"])
        self.tag_filters = set()

        # create the main window widget
        self.main_widget = QMainWindow()
        self.setWidget(self.main_widget)
        
        # create the table and the menu
        self.table = None
        self.createTable(objdict)
        self.createMenu()

        # set geometry
        w = 20
        for i in range(self.table.columnCount()):
            w += self.table.columnWidth(i)
        h = self.parent_widget.height() - 90
        x = self.parent_widget.x() + 10
        y = self.parent_widget.y() + 90
        self.setGeometry(x, y, w, h)

        # save manager object
        self.manager = manager

        self.show()
    
    def createMenu(self):
        """Create the menu for the object table widget."""
        # create the menubar object
        self.menubar = self.main_widget.menuBar()
        self.menubar.setNativeMenuBar(False) # attach menu to the window?

        menu = [
            {
                "attr_name": "listmenu",
                "text": "List",
                "opts":
                [
                    ("refresh_act", "Refresh", "", self.refresh),
                    {
                        "attr_name": "filtermenu",
                        "text": "Filter",
                        "opts":
                        [
                            ("refilter_act", "Regex filter...", "", self.setREFilter),
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
            },

            {
                "attr_name": "modifymenu",
                "text": "Modify",
                "opts":
                [
                    ("delete_act", "Delete", "", self.deleteObject),
                    ("rename_act", "Rename", "", self.renameObject)
                ]
            }
        ]

        # fill in the menu bar object
        populateMenuBar(self, self.menubar, menu)
    
    def setRow(self, obj_data : ObjectTableItem, row : int):
        """Set the data for a row of the table.
        
            Params:
                object_data (ObjectTableItem): the object containing the data for the object
                row (int): the row to enter this data into
        """
        self.table.setItem(row, 0, QTableWidgetItem(obj_data.name))
        col = 1
        if self.quantities["range"]:
            self.table.setItem(row, col, QTableWidgetItem(str(obj_data.getStart())))
            col += 1
            self.table.setItem(row, col, QTableWidgetItem(str(obj_data.getEnd())))
            col += 1
        if self.quantities["count"]:
            self.table.setItem(row, col, QTableWidgetItem(str(obj_data.getCount())))
            col += 1
        if self.quantities["flat_area"]:
            self.table.setItem(row, col, QTableWidgetItem(str(sigfigRound(obj_data.getFlatArea(), 6))))
            col += 1
        if self.quantities["volume"]:
            self.table.setItem(row, col, QTableWidgetItem(str(sigfigRound(obj_data.getVolume(), 6))))
    
    def passesFilters(self, item : ObjectTableItem):
        """Determine if an object will be displayed in the table based on existing filters.
        
            Params:
                item (ObjectTableItem): the item containing the data
        """
        # check tags
        object_tags = item.getTags()
        filters_len = len(self.tag_filters)
        if filters_len == 0:
            passes_tags = True
        else:
            object_len = len(object_tags)
            union_len = len(object_tags.union(self.tag_filters))
            if union_len < object_len + filters_len:  # intersection exists
                passes_tags = True
            else:
                passes_tags = False
        if not passes_tags:
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
        if self.quantities["range"]:
            self.horizontal_headers.append("Start")
            self.horizontal_headers.append("End")
        if self.quantities["count"]:
            self.horizontal_headers.append("Count")
        if self.quantities["flat_area"]:
            self.horizontal_headers.append("Flat Area")
        if self.quantities["volume"]:
            self.horizontal_headers.append("Volume")
        
        # filter the objects
        sorted_obj_names = sorted(list(objdict.keys()))
        filtered_obj_names = []
        for name in sorted_obj_names:
            if self.passesFilters(objdict[name]):
                filtered_obj_names.append(name)

        # create the table object
        self.table = QTableWidget(len(filtered_obj_names), len(self.horizontal_headers), self.main_widget)

        # format table
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
        self.table.resizeColumnsToContents()

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
        if objdata.isEmpty() and exists_in_table:
            self.table.removeRow(row)
            return
        if not exists_in_table:
            self.table.insertRow(row)
        self.setRow(objdata, row)
    
    def resizeEvent(self, event):
        """Resize the table when window is resized."""
        super().resizeEvent(event)
        w = event.size().width()
        h = event.size().height()
        self.table.resize(w, h-20)

    # MENU-RELATED FUNCTIONS

    def refresh(self):
        """Refresh the object lists."""
        self.manager.refresh()
    
    def setREFilter(self):
        """Set a new regex filter for the list."""
        # get a new filter from the user
        re_filter_str = ", ".join(self.re_filters)
        new_re_filter, confirmed = QInputDialog.getText(
            self,
            "Filter Objects",
            "Enter the object filter:",
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
    
    def setTagFilter(self):
        """Set a new tag filter for the list."""
        # get a new filter from the user
        tag_filter_str = ", ".join(self.tag_filters)
        new_tag_filter, confirmed = QInputDialog.getText(
            self,
            "Filter Objects",
            "Enter the tag filter:",
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
        
    def getSelectedObject(self) -> str:
        """Get the name of the object highlighted by the user.
        
            Returns:
                (str): the name of the object
        """
        selected_indexes = self.table.selectedIndexes()
        if len(selected_indexes) != 1 or selected_indexes[0].column() != 0:
            return None
        r = selected_indexes[0].row()
        obj_name = self.table.item(r, 0).text()
        return obj_name
    
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
    
    def deleteObject(self):
        """Delete an object from the entire series."""
        obj_name = self.getSelectedObject()
        if obj_name is None:
            return
        self.manager.deleteObject(obj_name)    
    
    def renameObject(self):
        """Rename an object in the entire series."""
        obj_name = self.getSelectedObject()
        if obj_name is None:
            return

        # ask the user for the new object name
        new_obj_name, confirmed = QInputDialog.getText(
            self,
            "Rename Object",
            "Enter the new object name:",
            text=str(obj_name)
        )
        if not confirmed or new_obj_name == obj_name:
            return
        
        self.manager.renameObject(obj_name, new_obj_name)
