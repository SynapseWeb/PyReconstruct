from PySide6.QtWidgets import QDockWidget, QTableWidget, QTableWidgetItem, QAbstractItemView, QMenuBar, QProgressDialog, QWidget
from PySide6.QtGui import QTransform
from PySide6.QtCore import Qt

from modules.recon.series import Series
from modules.recon.section import Section
from modules.gui.objecttableitem import ObjectTableItem
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
    
    def loadSeriesData(self, progbar : QProgressDialog):
        """Load all of the data for each object in the series.
        
            Params:
                progbar (QPorgressDialog): progress bar to update as function progresses
        """
        self._objdict = {}  # object name : ObjectTableItem (contains data on object)
        prog_value = 0
        final_value = len(self.series.sections)
        for section_num in self.series.sections:
            section = self.series.loadSection(section_num)
            t = section.tform
            point_tform = QTransform(t[0], t[3], t[1], t[4], t[2], t[5])
            for trace in section.traces:
                points = trace.points.copy()
                for i in range(len(points)):
                    points[i] = point_tform.map(*points[i])  # transform the points to get accurate data
                if trace.name not in self._objdict:
                    self._objdict[trace.name] = ObjectTableItem(trace.name)  # create new object if not already exists
                self._objdict[trace.name].addTrace(points, trace.closed, section_num, section.thickness)
            prog_value += 1
            progbar.setValue(prog_value / final_value * 100)
            if progbar.wasCanceled(): return
    
    def createTable(self):
        """Create the table widget."""
        # load all of the series data
        progbar = QProgressDialog("Loading object data...", "Cancel", 0, 100, self.parent_widget)
        progbar.setWindowTitle("Object Data")
        progbar.setWindowModality(Qt.WindowModal)
        self._objdict = {}
        self.loadSeriesData(progbar)
        if progbar.wasCanceled(): return

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
            self.table.setItem(row, 0, QTableWidgetItem(name))
            col = 1
            if self.quantities["range"]:
                self.table.setItem(row, col, QTableWidgetItem(str(trace_obj.getStart())))
                col += 1
                self.table.setItem(row, col, QTableWidgetItem(str(trace_obj.getEnd())))
                col += 1
            if self.quantities["count"]:
                self.table.setItem(row, col, QTableWidgetItem(str(trace_obj.getCount())))
                col += 1
            if self.quantities["flat_area"]:
                self.table.setItem(row, col, QTableWidgetItem(str(sigfigRound(trace_obj.getFlatArea(), 6))))
                col += 1
            if self.quantities["volume"]:
                self.table.setItem(row, col, QTableWidgetItem(str(sigfigRound(trace_obj.getVolume(), 6))))
                col += 1
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
    
    def updateSectionData(self, section_num, section : Section):
        objects_to_update = set()
        for name, item in self._objdict.items():
            had_existing_data = item.clearSectionData(section_num)
            if had_existing_data:
                objects_to_update.add(name)
        
        t = section.tform
        point_tform = QTransform(t[0], t[3], t[1], t[4], t[2], t[5])
        section_thickness = section.thickness
        for trace in section.traces:
            name = trace.name
            closed = trace.closed
            points = trace.points.copy()
            for i in range(len(points)):
                points[i] = point_tform.map(*points[i])  # transform the points to get accurate data
            if name not in self._objdict:
                self._objdict[name] = ObjectTableItem(name)  # create new object if not already exists
            self._objdict[name].addTrace(points, closed, section_num, section_thickness)
            objects_to_update.add(name)
        
        row = 0        
        for name in sorted(self._objdict.keys()):
            if self.table.item(row, 0) is None or self.table.item(row, 0).text() != name:
                self.table.insertRow(row)
            if name in objects_to_update:
                trace_obj = self._objdict[name]
                if trace_obj.isEmpty():
                    del self._objdict[name]
                    self.table.removeRow(row)
                    continue
                self.table.setItem(row, 0, QTableWidgetItem(name))
                col = 1
                if self.quantities["range"]:
                    self.table.setItem(row, col, QTableWidgetItem(str(trace_obj.getStart())))
                    col += 1
                    self.table.setItem(row, col, QTableWidgetItem(str(trace_obj.getEnd())))
                    col += 1
                if self.quantities["count"]:
                    self.table.setItem(row, col, QTableWidgetItem(str(trace_obj.getCount())))
                    col += 1
                if self.quantities["flat_area"]:
                    self.table.setItem(row, col, QTableWidgetItem(str(sigfigRound(trace_obj.getFlatArea(), 6))))
                    col += 1
                if self.quantities["volume"]:
                    self.table.setItem(row, col, QTableWidgetItem(str(sigfigRound(trace_obj.getVolume(), 6))))
                    col += 1
            row += 1
            
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
    
    def refresh(self):
        """Executed when user hits refresh: reloads all table data."""
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
    
    def resizeEvent(self, event):
        """Resize the table when window is resized."""
        super().resizeEvent(event)
        w = event.size().width()
        h = event.size().height()
        self.table.resize(w, h-20)
