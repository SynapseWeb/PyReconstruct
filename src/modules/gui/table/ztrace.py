import re
import os

from PySide6.QtWidgets import (
    QMainWindow, 
    QDockWidget, 
    QTableWidgetItem, 
    QAbstractItemView, 
    QWidget, 
    QInputDialog, 
    QMenu, 
    QFileDialog
)
from PySide6.QtCore import Qt

from .copy_table_widget import CopyTableWidget

from modules.datatypes import Series
from modules.gui.utils import (
    populateMenuBar,
    populateMenu,
    notify,
    noUndoWarning
)
from modules.gui.dialog import ZtraceDialog, SmoothZtraceDialog
from modules.constants import fd_dir

class ZtraceTableWidget(QDockWidget):

    def __init__(self, series : Series, mainwindow : QWidget, manager):
        """Create the object table dock widget.
        
            Params:
                series (Series): the series object
                mainwindow (QWidget): the main window the dock is connected to
                manager: the object table manager
        """
        # initialize the widget
        super().__init__(mainwindow)
        self.mainwindow = mainwindow
        self.series = series

        # set desired format for widget
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)  # ccan be docked to right or left side
        self.setWindowTitle("Ztrace List")

        self.re_filters = set([".*"])

        # create the main window widget
        self.main_widget = QMainWindow()
        self.setWidget(self.main_widget)
        
        # create the table and the menu
        self.table = None
        self.createTable()
        self.createMenus()

        # save manager object
        self.manager = manager

        self.show()
    
    def setRow(self, ztrace_name : str, row : int):
        """Populate a row with trace item data.
        
            Params:
                ztrace_name (str): the name of the ztrace
                row (int): the row to insert the data
        """
        if ztrace_name not in self.series.ztraces:
            self.table.removeRow(row)
        else:
            while row > self.table.rowCount()-1:
                self.table.insertRow(self.table.rowCount())
            col = 0
            self.table.setItem(row, col, QTableWidgetItem(ztrace_name))
            col += 1
            s = self.series.data.getZtraceStart(ztrace_name)
            self.table.setItem(row, col, QTableWidgetItem(
                str(s)
            ))
            col += 1
            e = self.series.data.getZtraceEnd(ztrace_name)
            self.table.setItem(row, col, QTableWidgetItem(
                str(e)
            ))
            col += 1
            d = self.series.data.getZtraceDist(ztrace_name)
            self.table.setItem(row, col, QTableWidgetItem(
                str(round(d, 5))
            ))
    
    def createMenus(self):
        """Create the menu for the trace table widget."""
        # Create menubar menu
        menubar_list = [
            {
                "attr_name": "listmenu",
                "text": "List",
                "opts":
                [
                    ("refresh_act", "Refresh", "", self.refresh),
                    ("export_act", "Export...", "", self.export),
                    ("refilter_act", "Regex filter...", "", self.setREFilter),
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
            ("editname_act", "Edit attributes...", "", self.editAttributes),
            ("smooth_act", "Smooth", "", self.smooth),
            None,
            {
                "attr_name": "menu_3D",
                "text": "3D",
                "opts":
                [
                    ("addto3D_act", "Add to scene", "", self.addTo3D),
                    ("remove3D_act", "Remove from scene", "", self.remove3D)
                ]
            },
            None,
            ("copy_act", "Copy", "", self.table.copy),
            None,
            ("delete_act", "Delete", "", self.delete)
        ]
        self.context_menu = QMenu(self)
        populateMenu(self, self.context_menu, context_menu_list)
            
    def passesFilters(self, ztrace_name):
        """Determine if an object will be displayed in the table based on existing filters.
        
            Params:
                ztrace_name (str): the name of the ztrace
        """        
        # check regex (will only be run if passes groups and tags)
        for re_filter in self.re_filters:
            if bool(re.fullmatch(re_filter, ztrace_name)):
                return True
        return False
    
    def format(self):
        """Format the rows and columns of the table."""
        self.table.resizeRowsToContents()
        self.table.resizeColumnsToContents()
    
    def createTable(self):
        """Create the table widget."""
        # establish table headers
        self.horizontal_headers = ["Name", "Start", "End", "Distance"]

        self.table = CopyTableWidget(0, len(self.horizontal_headers))

        # connect table functions
        self.table.contextMenuEvent = self.ztraceContextMenu
        self.table.mouseDoubleClickEvent = self.addTo3D
        
        # filter the objects
        sorted_ztrace_names = sorted(list(self.series.ztraces.keys()))
        filetered_ztrace_list = []
        for name in sorted_ztrace_names:
            if self.passesFilters(name):
                filetered_ztrace_list.append(name)

        # format table
        self.table.setWordWrap(False)
        self.table.setShowGrid(False)  # no grid
        self.table.setAlternatingRowColors(True)  # alternate row colors
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # cannot be edited
        self.table.setHorizontalHeaderLabels(self.horizontal_headers)  # titles
        self.table.verticalHeader().hide()  # no veritcal header
        
        # fill in object data
        for r, name in enumerate(filetered_ztrace_list):
            self.setRow(name, r)

        # format rows and columns
        self.format()

        # set table as central widget
        self.main_widget.setCentralWidget(self.table)
    
    def updateZtraces(self, ztrace_names : set):
        """Update the specified ztraces."""
        for name in ztrace_names:
            r = 0
            while self.table.item(r, 0).text() < name:
                r += 1
            if self.table.item(r, 0).text() != name:
                self.table.insertRow(r)
            self.setRow(name, r)
    
    def getSelectedName(self):
        """Get the trace item that is selected by the user."""
        selected_indeces = self.table.selectedIndexes()
        if len(selected_indeces) != 1:
            return
        return self.table.item(selected_indeces[0].row(), 0).text()
    
    def getSelectedNames(self):
        """Get the trace items that iare selected by the user."""
        selected_indeces = self.table.selectedIndexes()
        if len(selected_indeces) < 1:
            return
        return [
            self.table.item(i.row(), 0).text() for i in selected_indeces
        ]    
    
    def resizeEvent(self, event):
        """Resize the table when window is resized."""
        super().resizeEvent(event)
        w = event.size().width()
        h = event.size().height()
        self.table.resize(w, h-20)

    # RIGHT CLICK FUNCTIONS

    def ztraceContextMenu(self, event=None):
        """Executed when button is right-clicked: pulls up menu for user to modify objects."""
        if len(self.table.selectedIndexes()) == 0:
            return
        self.context_menu.exec(event.globalPos())

    def editAttributes(self):
        """Edit the name of a ztrace."""
        names = self.getSelectedNames()
        if names is None:
            return
        if len(names) > 1:
            notify("Please modify one ztrace at a time.")
            return
        name = names[0]

        if name not in self.series.ztraces:
            return
        ztrace = self.series.ztraces[name]

        attributes, confirmed = ZtraceDialog(
            self,
            name=name,
            color=ztrace.color
        ).exec()

        if not confirmed:
            return

        new_name, new_color = attributes

        if new_name != name and new_name in self.series.ztraces:
            notify("This ztrace already exists.")
            return
        
        self.manager.editAttributes(name, new_name, new_color)
    
    def smooth(self):
        """Smooth a set of ztraces."""
        names = self.getSelectedNames()
        if not names:
            return
        
        response, confirmed = SmoothZtraceDialog(self).exec()
        if not confirmed:
            return
        
        smooth, newztrace = response
        
        self.manager.smooth(names, smooth, newztrace)
    
    def addTo3D(self, event=None):
        """Add the ztrace to the 3D scene."""
        names = self.getSelectedNames()
        if not names:
            return
        
        self.manager.addTo3D(names)
    
    def remove3D(self):
        """Remove the ztrace from the 3D scene."""
        names = self.getSelectedNames()
        if not names:
            return
        
        self.manager.remove3D(names)
    
    def delete(self):
        """Delete a set of ztraces."""
        names = self.getSelectedNames()
        if not names:
            return
        
        # confirm with user
        if not noUndoWarning():
            return
        
        self.manager.delete(names)

    # MENU-RELATED FUNCTIONS

    def refresh(self):
        """Refresh the tables."""
        self.manager.refresh()
    
    def export(self):
        """Export the trace list as a csv file."""
        # get the location from the user
        global fd_dir
        file_path, ext = QFileDialog.getSaveFileName(
            self,
            "Save Ztrace List",
            os.path.join(fd_dir.get(), "ztraces.csv"),
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
        # trace data
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
            "Filter Ztraces",
            "Enter the ztrace filters:",
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
    
    def closeEvent(self, event):
        """Remove self from manager table list."""
        self.manager.tables.remove(self)
        super().closeEvent(event)
