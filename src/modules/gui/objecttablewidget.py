from PySide6.QtWidgets import QMainWindow, QDockWidget, QTableWidget, QTableWidgetItem, QAbstractItemView, QProgressDialog, QWidget, QInputDialog
from PySide6.QtCore import Qt
from modules.backend.gui_functions import populateMenuBar

from modules.pyrecon.series import Series
from modules.pyrecon.section import Section

from modules.backend.object_table_item import ObjectTableItem
from modules.backend.object_table_functions import loadSeriesData, getObjectsToUpdate, deleteObject, renameObject

from modules.calc.quantification import sigfigRound

class ObjectTableWidget(QDockWidget):

    def __init__(self, series : Series, quantities : dict, parent : QWidget):
        """Create the object table dock widget.
        
            Params:
                series (Series): the Series object
                quantities (dict): information on which calculations to include
                parent (QWidget): the main window the dock is connected to
        """
        # initialize the widget
        super().__init__(parent)
        self.series = series
        self.quantities = quantities
        self.parent_widget = parent

        # set desired format for widget
        self.setFloating(True)  # not docked to the window
        self.setAllowedAreas(Qt.NoDockWidgetArea)  # cannot be docked to the window
        self.setWindowTitle("Object List")

        # create the main window widget
        self.main_widget = QMainWindow()
        self.setWidget(self.main_widget)
        
        # create the table and the menu
        self.createTable()
        self.createMenu()

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
                    ("refresh_act", "Refresh", "", self.refresh)
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
    
    def deleteEmptyObjects(self):
        """Remove any objects that are empty from the dictionary and the table."""
        row = 0
        for name in sorted(list(self.objdata.keys())):
            if self.objdata[name].isEmpty():
                del(self.objdata[name])
                self.table.removeRow(row)
            else:
                row += 1
    
    def updateTable(self, objects_to_update : list = None):
        """Populate the table based on self.objdata.
        
            Params:
                objects_to_update (list): list of object that need to be updated
        """
        update_all = (objects_to_update is None)
        sorted_obj_names = sorted(list(self.objdata.keys()))
        if update_all:  # update all objects if requested
            row = 0
            for name in sorted_obj_names:
                if row >= self.table.rowCount():
                    self.table.insertRow(row)
                self.setRow(self.objdata[name], row)
                row += 1
            # clean up hanging rows with data
            while row < self.table.rowCount():
                self.table.removeRow(row)
        else:  # update only requested objects
            for i in range(len(sorted_obj_names)):
                obj_name = sorted_obj_names[i]
                if self.table.item(i, 0) == obj_name:  # if the object is found to be in the right place
                    if obj_name in objects_to_update:
                        self.setRow(self.objdata[obj_name], i)
                else:  # if the object is not in the table
                    self.table.insertRow(i)
                    self.setRow(self.objdata[obj_name], i)
        
        # check for objects that no longer exist in the series
        self.deleteEmptyObjects()

        # resize the table
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
    
    def refresh(self):
        """Reload all of the series data.
        
        (Example: when alignment is changed)"""
        progbar = QProgressDialog("Refreshing object data...", "Cancel", 0, 100, self.parent_widget)
        progbar.setWindowTitle("Object Data")
        progbar.setWindowModality(Qt.WindowModal)
        self.objdata = loadSeriesData(self.series, progbar)
        self.updateTable()

    def getRowIndex(self, obj_name : str):
        """Get the row index of an object in the table (or where it SHOULD be on the table).
        
            Parmas:
                obj_name (str): the name of the object
            Returns:
                (int): the row index for that object in the table
        """
        for row_index in self.table.rowCount():
            row_name = self.table.item(row_index, 0).text()
            if obj_name <= row_name:
                return row_index
        return self.table.rowCount() + 1
    
    def createTable(self):
        """Create the table widget."""
        # load all of the series data
        progbar = QProgressDialog("Loading object data...", "Cancel", 0, 100, self.parent_widget)
        progbar.setWindowTitle("Object Data")
        progbar.setWindowModality(Qt.WindowModal)
        self.objdata = loadSeriesData(self.series, progbar)

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
        
        # create the table object
        self.table = QTableWidget(len(self.objdata), len(self.horizontal_headers), self.main_widget)

        # format table
        self.table.setShowGrid(False)  # no grid
        self.table.setAlternatingRowColors(True)  # alternate row colors
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # cannot be edited
        self.table.setHorizontalHeaderLabels(self.horizontal_headers)  # titles
        self.table.verticalHeader().hide()  # no veritcal header

        # fill in object data
        self.updateTable()  # create the table

        # more table formatting
        w = 20
        for i in range(self.table.columnCount()):
            w += self.table.columnWidth(i)
        h = self.parent_widget.height()
        self.resize(w, h)
        self.table.setGeometry(0, 20, w, h-20)

        # set table as central widget
        self.main_widget.setCentralWidget(self.table)
    
    def updateSectionData(self, section_num : int, section : Section):
        """Auto-refresh the table when a section is saved.
        
            Params:
                secion_num (int): the section number
                section (Section): the section object
        """
        # get the name of objects that need to be updated
        objects_to_update = getObjectsToUpdate(self.objdata, section_num, self.series, section)

        # update the objects
        self.updateTable(objects_to_update)
    
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
        obj_item = self.objdata[obj_name]
        obj_section = obj_item.getStart()
        self.parent_widget.setToObject(obj_name, obj_section)
    
    def findLast(self):
        """Focus the field on the last occurence of an object in the series."""
        obj_name = self.getSelectedObject()
        if obj_name is None:
            return
        obj_item = self.objdata[obj_name]
        obj_section = obj_item.getEnd()
        self.parent_widget.setToObject(obj_name, obj_section)
    
    def deleteObject(self):
        """Delete an object from the entire series."""
        # get the object to delete
        obj_name = self.getSelectedObject()
        if obj_name is None:
            return
        # delete the object on every section
        deleteObject(self.series, obj_name)
        # update the table
        row_index = self.getRowIndex(obj_name)
        self.table.removeRow(row_index)
        # update the data dict
        del(self.objdata[obj_name])
        # reload the current field view
        self.parent_widget.field.reload()      
    
    def renameObject(self):
        """Rename an object in the entire series."""
        # get the object to rename
        selected_indexes = self.table.selectedIndexes()
        if len(selected_indexes) != 1 or selected_indexes[0].column() != 0:
            return
        r = selected_indexes[0].row()
        obj_name = self.table.item(r, 0).text()

        # ask the user for the new object name
        new_obj_name, confirmed = QInputDialog.getText(
            self,
            "Rename Object",
            "Enter the new object name:",
            text=str(obj_name)
        )
        if not confirmed or new_obj_name == obj_name:
            return

        # rename the object on all the sections
        renameObject(self.series, obj_name, new_obj_name)

        # change the data in the table
        # if new name already exists, combine the data
        if new_obj_name in self.objdata:
            # combine the table objects
            combined = self.objdata[new_obj_name].combine(self.objdata[obj_name])
            self.objdata[new_obj_name] = combined
            # remove old object from table and data
            old_index = self.getRowIndex(obj_name)
            self.table.removeRow(old_index)
            del(self.objdata[obj_name])
            # update the data in new object
            new_index = self.getRowIndex(new_obj_name)
            self.setRow(combined, new_index)
        # if the name does not exist, create a new object
        else:
            # rename in dictionary
            self.objdata[new_obj_name] = self.objdata[obj_name]
            self.objdata[new_obj_name].name = new_obj_name
            # remove old object from table and data
            old_index = self.getRowIndex(obj_name)
            self.table.removeRow(old_index)
            del(self.objdata[obj_name])
            # add row to table
            new_index = self.getRowIndex(obj_name)
            self.table.insertRow(new_index)
            self.setRow(self.objdata[new_obj_name])
        
        # reload the current field view
        self.parent_widget.field.reload()
    
    def resizeEvent(self, event):
        """Resize the table when window is resized."""
        super().resizeEvent(event)
        w = event.size().width()
        h = event.size().height()
        self.table.resize(w, h-20)
