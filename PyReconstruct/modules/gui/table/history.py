from PySide6.QtWidgets import QDockWidget, QWidget, QTableWidgetItem, QAbstractItemView
from PySide6.QtCore import Qt

from .copy_table_widget import CopyTableWidget

from PyReconstruct.modules.datatypes import LogSet, Log

class HistoryTableWidget(QDockWidget):

    def __init__(self, log_set : LogSet, mainwindow : QWidget, obj_names : list = None):
        """Create a text widget to display history"""
        super().__init__(mainwindow)
        self.mainwindow = mainwindow

        self.setFloating(True)
        self.setAllowedAreas(Qt.NoDockWidgetArea)
        self.setWindowTitle("History")

        # filter the logs
        self.filterLogs(log_set, obj_names)
        
        # create the table
        self.createTable(log_set)

        self.resize(self.sizeHint())

        self.show()
    
    def filterLogs(self, log_set : LogSet, obj_names : list):
        """Remove logs unrelated to objects of interest."""
        if not obj_names:
            return
        
        i = 0
        while i < len(log_set.all_logs):
            log = log_set.all_logs[i]
            if log.obj_name not in obj_names:
                log_set.all_logs.pop(i)
            else:
                i += 1

    def setRow(self, r : int, log : Log):
        """Set the data for a row.
        
            Params:
                r (int): the row index
                snum (int): the section number
        """
        for c, s in enumerate(str(log).strip().split(", ")):
            self.table.setItem(r, c, QTableWidgetItem(s))
    
    def createTable(self, log_set : LogSet):
        """Create the table widget."""
        # establish table headers
        self.horizontal_headers = ["Date", "Time", "User", "Object", "Sections", "Event"]

        self.table = CopyTableWidget(self, len(log_set.all_logs), len(self.horizontal_headers))
        self.setWidget(self.table)

        # format table
        self.table.setShowGrid(False)  # no grid
        self.table.setAlternatingRowColors(True)  # alternate row colors
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # cannot be edited
        self.table.setHorizontalHeaderLabels(self.horizontal_headers)  # titles
        self.table.verticalHeader().hide()  # no veritcal header
        
        # fill in section data
        for r, log in enumerate(reversed(log_set.all_logs)):
            self.setRow(r, log)
        
        # format the table
        self.table.resizeColumnsToContents()