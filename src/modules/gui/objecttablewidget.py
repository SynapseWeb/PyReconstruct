from PySide6.QtWidgets import QDockWidget, QTableWidget, QTableWidgetItem, QAbstractItemView, QMenuBar, QProgressDialog, QWidget
from PySide6.QtCore import Qt

from modules.pyrecon.series import Series
from modules.pyrecon.section import Section

from modules.backend.object_table_data import ObjectTableItem, loadSeriesData, getObjectsToUpdate

from modules.calc.quantification import sigfigRound

class ObjectTableWidget(QDockWidget):

    def __init__(self, series : Series, quantities : dict, parent : QWidget):
        """Create the object table dock widget.
        
            Params:
                series (Series): the Series object
                quantities (dict): information on which calculations to include
                parent (QWidget): the main window the dock is connected to
        """
        super().__init__(parent)
        self.series = series
        self.quantities = quantities
        self.parent_widget = parent

        self.setFloating(True)  # not docked to the window
        self.setAllowedAreas(Qt.NoDockWidgetArea)  # cannot be docked to the window
        self.setWindowTitle("Object List")
        self.central_widget = QWidget()
        self.setWidget(self.central_widget)

        self.menubar = QMenuBar(self.central_widget)
        self.listmenu = self.menubar.addMenu("List")
        self.refresh_act = self.listmenu.addAction("Refresh")
        self.refresh_act.triggered.connect(self.refresh)
        self.findfirst_act = self.menubar.addAction("Find First!")
        self.findfirst_act.triggered.connect(self.findFirst)
        self.findlast_act = self.menubar.addAction("Find Last!")
        self.findlast_act.triggered.connect(self.findLast)
        
        self.createTable()

        self.show()
    
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
        self._objdict = loadSeriesData(self.series, progbar)
        # create the table
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
        self.table = QTableWidget(len(self._objdict), len(self.horizontal_headers), self.central_widget)
        row = 0
        # load the collected data into the table
        for name in sorted(self._objdict.keys()):
            trace_obj = self._objdict[name]
            self.setRow(trace_obj, row)
            row += 1
        self.table.setShowGrid(False)  # no grid
        self.table.setAlternatingRowColors(True)  # alternate row colors
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # cannot be edited
        self.table.setHorizontalHeaderLabels(self.horizontal_headers)  # titles
        self.table.verticalHeader().hide()  # no veritcal header
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
        w = 20
        for i in range(self.table.columnCount()):
            w += self.table.columnWidth(i)
        h = self.parent_widget.height()
        self.resize(w, h)
        self.table.setGeometry(0, 20, w, h-20)
    
    def updateSectionData(self, section_num : int, section : Section):
        """Auto-refresh the table when a section is saved.
        
            Params:
                secion_num (int): the section number
                section (Section): the section object
        """
        # get the name of objects that need to be updated
        objects_to_update = getObjectsToUpdate(self._objdict, section_num, self.series, section)
        # iterate through every object
        row = 0        
        for name in sorted(self._objdict.keys()):
            # create a new row if the name does not exist on the table
            if self.table.item(row, 0) is None or self.table.item(row, 0).text() != name:
                self.table.insertRow(row)
            # update the data on the table if the object was on the section
            if name in objects_to_update:
                trace_obj = self._objdict[name]
                # delete the object if no data is found for it
                if trace_obj.isEmpty():
                    del self._objdict[name]
                    self.table.removeRow(row)
                    continue
                # update data
                self.setRow(trace_obj, row)
            row += 1
            
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
    
    def refresh(self):
        """Executed when user hits refresh: reloads table data."""
        self.parent_widget.saveAllData()
    
    def findFirst(self):
        """Focus the field on the first occurence of an object in the series."""
        selected_indexes = self.table.selectedIndexes()
        if len(selected_indexes) != 1 or selected_indexes[0].column() != 0:
            return
        r = selected_indexes[0].row()
        obj_name = self.table.item(r, 0).text()
        obj_item = self._objdict[obj_name]
        obj_section = obj_item.getStart()
        self.parent_widget.setToObject(obj_name, obj_section)
    
    def findLast(self):
        """Focus the field on the last occurence of an object in the series."""
        selected_indexes = self.table.selectedIndexes()
        if len(selected_indexes) != 1 or selected_indexes[0].column() != 0:
            return
        r = selected_indexes[0].row()
        obj_name = self.table.item(r, 0).text()
        obj_item = self._objdict[obj_name]
        obj_section = obj_item.getEnd()
        self.parent_widget.setToObject(obj_name, obj_section)
    
    def deleteObject(self, series : Series, obj_name : str):
        """Delete on object from the whole series.
        
            Params:
                series (Series): the series object
                obj_name (str): the name of the object
        """
        # delete the object on each section
        for snum in series.sections:
            section = series.loadSection(snum)
            del(section.traces[obj_name])
            section.save()
        # update the table
        row_index = self.getRowIndex(obj_name)
        self.table.removeRow(row_index)
        # update the data dict
        del(self._objdict[obj_name])        
    
    def renameObject(self, series : Series, obj_name : str, new_obj_name : str):
        """Rename an object in the whole series.
        
            Params:
                series (Series): the series object
                obj_name (str): the name of the object to be changed
                new_obj_name (str): the new name for this object
        """
        # rename the object on each section
        for snum in series.sections:
            section = series.loadSection(snum)
            for trace in section.traces[obj_name]:
                trace.name = new_obj_name
            # check if the new name exists in the section
            if new_obj_name in section.traces:
                section.traces[new_obj_name] += section.traces[obj_name]
            else:
                section.traces[new_obj_name] = section.traces[obj_name]
            del(section.traces[obj_name])
        # if new name already exists, combine the data
        if new_obj_name in self._objdict:
            # combine the table objects
            combined = self._objdict[new_obj_name].combine(self._objdict[obj_name])
            self._objdict[new_obj_name] = combined
            # remove old object from table and data
            old_index = self.getRowIndex(obj_name)
            self.table.removeRow(old_index)
            del(self._objdict[obj_name])
            # update the data in new object
            new_index = self.getRowIndex(new_obj_name)
            self.setRow(combined, new_index)
        # if the name does not exist, create a new object
        else:
            # rename in dictionary
            self._objdict[new_obj_name] = self._objdict[obj_name]
            self._objdict[new_obj_name].name = new_obj_name
            # remove old object from table and data
            old_index = self.getRowIndex(obj_name)
            self.table.removeRow(old_index)
            del(self._objdict[obj_name])
            # add row to table
            new_index = self.getRowIndex(obj_name)
            self.table.insertRow(new_index)
            self.setRow(self._objdict[new_obj_name])
    
    def resizeEvent(self, event):
        """Resize the table when window is resized."""
        super().resizeEvent(event)
        w = event.size().width()
        h = event.size().height()
        self.table.resize(w, h-20)
