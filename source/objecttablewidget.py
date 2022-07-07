import json
from PySide2.QtWidgets import QDockWidget, QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView
from PySide2.QtCore import Qt

from objecttableitem import ObjectTableItem

class ObjectTableWidget(QDockWidget):

    def __init__(self, series, wdir, quantities, parent):
        super().__init__(parent)
        self.series = series
        self.wdir = wdir
        self.quantities = quantities

        self.setFloating(True)
        self.setAllowedAreas(Qt.NoDockWidgetArea)
        self.setWindowTitle("Object List")

        self._objdict = {}
        self.loadSeriesData()

        horizontal_headers = ["Name"]
        if quantities["range"]:
            horizontal_headers.append("Start")
            horizontal_headers.append("End")
        if quantities["count"]:
            horizontal_headers.append("Count")
        if quantities["surface_area"]:
            horizontal_headers.append("Surface Area")
        if quantities["flat_area"]:
            horizontal_headers.append("Flat Area")
        if quantities["volume"]:
            horizontal_headers.append("Volume")
        print(horizontal_headers)
        self.table = QTableWidget(len(self._objdict), len(horizontal_headers))
        row = 0
        for name in sorted(self._objdict.keys()):
            trace_obj = self._objdict[name]
            self.table.setItem(row, 0, QTableWidgetItem(name))
            col = 1
            if quantities["range"]:
                self.table.setItem(row, col, QTableWidgetItem(str(trace_obj.start)))
                col += 1
                self.table.setItem(row, col, QTableWidgetItem(str(trace_obj.end)))
                col += 1
            if quantities["count"]:
                self.table.setItem(row, col, QTableWidgetItem(str(trace_obj.count)))
                col += 1
            if quantities["surface_area"]:
                self.table.setItem(row, col, QTableWidgetItem(str(round(trace_obj.surface_area, 6))))
                col += 1
            if quantities["flat_area"]:
                self.table.setItem(row, col, QTableWidgetItem(str(round(trace_obj.flat_area, 6))))
                col += 1
            if quantities["volume"]:
                self.table.setItem(row, col, QTableWidgetItem(str(round(trace_obj.volume, 6))))
                col += 1
            row += 1
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setHorizontalHeaderLabels(horizontal_headers)
        self.table.verticalHeader().hide()
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
        total_w = 5
        for i in range(self.table.columnCount()):
            total_w += self.table.columnWidth(i)
        self.setWidget(self.table)
        self.resize(total_w, parent.height())
        self.show()

    def loadSeriesData(self):
        self._objdict = {}
        for i in range(len(self.series.sections)):
            section = self.series.sections[i]
            section_num = int(section[section.rfind(".")+1:])
            with open(self.wdir + section, "r") as section_file:
                section_data = json.load(section_file)
            section_thickness = section_data["thickness"]
            for trace in section_data["traces"]:
                name = trace["name"]
                closed = trace["closed"]
                points = trace["points"]
                if name not in self._objdict:
                    self._objdict[name] = ObjectTableItem(name)
                self._objdict[name].addTrace(points, closed, section_num, section_thickness)