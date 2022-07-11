import orjson
from PySide2.QtWidgets import QDockWidget, QTableWidget, QTableWidgetItem, QAbstractItemView, QMenuBar, QProgressDialog, QWidget
from PySide2.QtGui import QTransform
from PySide2.QtCore import Qt, QModelIndex

from objecttableitem import ObjectTableItem
from quantification import sigfigRound

class ObjectTableWidget(QDockWidget):

    def __init__(self, series, wdir, quantities, parent):
        super().__init__(parent)
        self.series = series
        self.wdir = wdir
        self.quantities = quantities
        self.parent_widget = parent

        self.setFloating(True)
        self.setAllowedAreas(Qt.NoDockWidgetArea)
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
    
    def createTable(self):
        progbar = QProgressDialog("Loading object data...", "Cancel", 0, 100, self.parent_widget)
        progbar.setWindowTitle("Object Data")
        progbar.setWindowModality(Qt.WindowModal)
        self._objdict = {}
        self.loadSeriesData(progbar)
        if progbar.wasCanceled(): return

        horizontal_headers = ["Name"]
        if self.quantities["range"]:
            horizontal_headers.append("Start")
            horizontal_headers.append("End")
        if self.quantities["count"]:
            horizontal_headers.append("Count")
        if self.quantities["surface_area"]:
            horizontal_headers.append("Surface Area")
        if self.quantities["flat_area"]:
            horizontal_headers.append("Flat Area")
        if self.quantities["volume"]:
            horizontal_headers.append("Volume")
        self.table = QTableWidget(len(self._objdict), len(horizontal_headers), self.central_widget)
        row = 0
        for name in sorted(self._objdict.keys()):
            trace_obj = self._objdict[name]
            self.table.setItem(row, 0, QTableWidgetItem(name))
            col = 1
            if self.quantities["range"]:
                self.table.setItem(row, col, QTableWidgetItem(str(trace_obj.start)))
                col += 1
                self.table.setItem(row, col, QTableWidgetItem(str(trace_obj.end)))
                col += 1
            if self.quantities["count"]:
                self.table.setItem(row, col, QTableWidgetItem(str(trace_obj.count)))
                col += 1
            if self.quantities["surface_area"]:
                self.table.setItem(row, col, QTableWidgetItem(str(sigfigRound(trace_obj.surface_area, 6))))
                col += 1
            if self.quantities["flat_area"]:
                self.table.setItem(row, col, QTableWidgetItem(str(sigfigRound(trace_obj.flat_area, 6))))
                col += 1
            if self.quantities["volume"]:
                self.table.setItem(row, col, QTableWidgetItem(str(sigfigRound(trace_obj.volume, 6))))
                col += 1
            row += 1
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setHorizontalHeaderLabels(horizontal_headers)
        self.table.verticalHeader().hide()
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
        w = 20
        for i in range(self.table.columnCount()):
            w += self.table.columnWidth(i)
        h = self.parent_widget.height()
        self.resize(w, h)
        self.table.setGeometry(0, 20, w, h-20)

    def loadSeriesData(self, progbar):
        self._objdict = {}
        prog_value = 0
        final_value = len(self.series.sections)
        for section_num in self.series.sections:
            section = self.series.sections[section_num]
            with open(self.wdir + section, "rb") as section_file:
                section_data = orjson.loads(section_file.read())
            section_thickness = section_data["thickness"]
            t = section_data["tform"]
            point_tform = QTransform(t[0], t[3], t[1], t[4], t[2], t[5])
            for trace in section_data["traces"]:
                name = trace["name"]
                closed = trace["closed"]
                points = trace["points"]
                for i in range(len(points)):
                    points[i] = point_tform.map(*points[i])
                if name not in self._objdict:
                    self._objdict[name] = ObjectTableItem(name)
                self._objdict[name].addTrace(points, closed, section_num, section_thickness)
            prog_value += 1
            progbar.setValue(prog_value / final_value * 100)
            if progbar.wasCanceled(): return
    
    def refresh(self):
        self.parent_widget.saveAllData()
        self.createTable()
    
    def findFirst(self):
        selected_indexes = self.table.selectedIndexes()
        if len(selected_indexes) != 1 or selected_indexes[0].column() != 0:
            return
        r = selected_indexes[0].row()
        obj_name = self.table.item(r, 0).text()
        obj_item = self._objdict[obj_name]
        obj_section = obj_item.start
        self.parent_widget.setToObject(obj_name, obj_section)
    
    def findLast(self):
        selected_indexes = self.table.selectedIndexes()
        if len(selected_indexes) != 1 or selected_indexes[0].column() != 0:
            return
        r = selected_indexes[0].row()
        obj_name = self.table.item(r, 0).text()
        obj_item = self._objdict[obj_name]
        obj_section = obj_item.end
        self.parent_widget.setToObject(obj_name, obj_section)
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = event.size().width()
        h = event.size().height()
        self.table.resize(w, h-20)
