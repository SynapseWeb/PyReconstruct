import orjson
from PySide2.QtWidgets import QDockWidget, QTableWidget, QTableWidgetItem, QAbstractItemView, QMenuBar, QProgressDialog, QWidget
from PySide2.QtGui import QTransform
from PySide2.QtCore import Qt, QModelIndex

from series import Series
from objecttableitem import ObjectTableItem
from quantification import sigfigRound

class ObjectTableWidget(QDockWidget):

    def __init__(self, series : Series, wdir : str, quantities : dict, parent : QWidget):
        """Creat the object table dock widget.
        
            Params:
                series (Series): the Series object
                wdir (str): the directory containing the JSON files
                quantities (dict): information on which calculations to include
                parent (QWidget): the main window the dock is connected to"""
        super().__init__(parent)
        self.series = series
        self.wdir = wdir
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
        # load the collected data into the table
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
        self.table.setShowGrid(False)  # no grid
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # cannot be edited
        self.table.setHorizontalHeaderLabels(horizontal_headers)  # titles
        self.table.verticalHeader().hide()  # no veritcal header
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
        w = 20
        for i in range(self.table.columnCount()):
            w += self.table.columnWidth(i)
        h = self.parent_widget.height()
        self.resize(w, h)
        self.table.setGeometry(0, 20, w, h-20)

    def loadSeriesData(self, progbar : QProgressDialog):
        """Load all of the data for each object in the series.
        
            Params:
                progbar (QPorgressDialog): progress bar to update as function progresses
        """
        self._objdict = {}  # object name : ObjectTableItem (contains data on object)
        prog_value = 0
        final_value = len(self.series.sections)
        for section_num in self.series.sections:
            section = self.series.sections[section_num]
            with open(self.wdir + section, "rb") as section_file:
                section_data = orjson.loads(section_file.read())  # orjson was mildly faster?
            section_thickness = section_data["thickness"]
            t = section_data["tform"]
            point_tform = QTransform(t[0], t[3], t[1], t[4], t[2], t[5])
            for trace in section_data["traces"]:
                name = trace["name"]
                closed = trace["closed"]
                points = trace["points"]
                for i in range(len(points)):
                    points[i] = point_tform.map(*points[i])  # transform the points to get accurate data
                if name not in self._objdict:
                    self._objdict[name] = ObjectTableItem(name)  # create new object if not already exists
                self._objdict[name].addTrace(points, closed, section_num, section_thickness)
            prog_value += 1
            progbar.setValue(prog_value / final_value * 100)
            if progbar.wasCanceled(): return
    
    def refresh(self):
        """Executed when user hits refresh: reloads all table data."""
        self.parent_widget.saveAllData()
        self.createTable()
    
    def findFirst(self):
        """Focus the field on the first occurence of an object in the series."""
        selected_indexes = self.table.selectedIndexes()
        if len(selected_indexes) != 1 or selected_indexes[0].column() != 0:
            return
        r = selected_indexes[0].row()
        obj_name = self.table.item(r, 0).text()
        obj_item = self._objdict[obj_name]
        obj_section = obj_item.start
        self.parent_widget.setToObject(obj_name, obj_section)
    
    def findLast(self):
        """Focus the field on the last occurence of an object in the series."""
        selected_indexes = self.table.selectedIndexes()
        if len(selected_indexes) != 1 or selected_indexes[0].column() != 0:
            return
        r = selected_indexes[0].row()
        obj_name = self.table.item(r, 0).text()
        obj_item = self._objdict[obj_name]
        obj_section = obj_item.end
        self.parent_widget.setToObject(obj_name, obj_section)
    
    def resizeEvent(self, event):
        """Resize the table when window is resized."""
        super().resizeEvent(event)
        w = event.size().width()
        h = event.size().height()
        self.table.resize(w, h-20)
