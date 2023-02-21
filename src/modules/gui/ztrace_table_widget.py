import re

from PySide6.QtWidgets import (
    QMainWindow, 
    QDockWidget, 
    QTableWidget, 
    QTableWidgetItem, 
    QAbstractItemView, 
    QWidget, 
    QInputDialog, 
    QMenu, 
    QFileDialog, 
    QMessageBox
)
from PySide6.QtCore import Qt

from modules.pyrecon.series import Series

from modules.backend.ztrace_table_item import ZtraceTableItem
from modules.gui.gui_functions import populateMenuBar, populateMenu, notify
from modules.gui.dialog import ZtraceDialog

class ZtraceTableWidget(QDockWidget):

    def __init__(self, series : Series, ztracedict : dict, mainwindow : QWidget, manager):
        """Create the object table dock widget.
        
            Params:
                series (Series): the series object
                ztracedict (dict): contains all ztrace info for the table
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
        self.createTable(ztracedict)
        self.createMenus()

        # save manager object
        self.manager = manager

        self.show()
    
    def setRow(self, ztraceitem : ZtraceTableItem, row : int):
        """Populate a row with trace item data.
        
            Params:
                ztraceitem (ZtraceTableItem): the object contianing the ztrace table data
                row (int): the row to insert the data
        """
        while row > self.table.rowCount()-1:
            self.table.insertRow(self.table.rowCount())
        col = 0
        self.table.setItem(row, col, QTableWidgetItem(ztraceitem.name))
        col += 1
        self.table.setItem(row, col, QTableWidgetItem(
            str(round(ztraceitem.getDist(), 5))
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
            ("addto3D_act", "Add to 3D scene", "", self.addTo3D),
            None,
            ("delete_act", "Delete", "", self.delete)
        ]
        self.context_menu = QMenu(self)
        populateMenu(self, self.context_menu, context_menu_list)
            
    def passesFilters(self, item : ZtraceTableItem):
        """Determine if an object will be displayed in the table based on existing filters.
        
            Params:
                item (ZtraceTableItem): the item containing the data
        """        
        # check regex (will only be run if passes groups and tags)
        for re_filter in self.re_filters:
            if bool(re.fullmatch(re_filter, item.name)):
                return True
        return False
    
    def format(self):
        """Format the rows and columns of the table."""
        self.table.resizeRowsToContents()
        self.table.resizeColumnsToContents()
    
    def createTable(self, ztracedict : dict):
        """Create the table widget.
        
            Params:
                ztracedict (dict): the dictionary containing the object table data objects
        """
        self.table = QTableWidget(0, 2)

        # connect table functions
        self.table.contextMenuEvent = self.ztraceContextMenu
        self.table.mouseDoubleClickEvent = self.addTo3D

        # establish table headers
        self.horizontal_headers = ["Name", "Distance"]
        
        # filter the objects
        sorted_ztrace_names = sorted(list(ztracedict.keys()))
        self.items = []
        for name in sorted_ztrace_names:
            item = ztracedict[name]
            if self.passesFilters(item):
                self.items.append(item)

        # format table
        self.table.setWordWrap(False)
        self.table.setShowGrid(False)  # no grid
        self.table.setAlternatingRowColors(True)  # alternate row colors
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # cannot be edited
        self.table.setHorizontalHeaderLabels(self.horizontal_headers)  # titles
        self.table.verticalHeader().hide()  # no veritcal header
        
        # fill in object data
        for r, item in enumerate(self.items):
            self.setRow(item, r)

        # format rows and columns
        self.format()

        # set table as central widget
        self.main_widget.setCentralWidget(self.table)
    
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
        for ztrace in self.series.ztraces:
            if ztrace.name == name:
                break

        attributes, confirmed = ZtraceDialog(
            self,
            name=name,
            color=ztrace.color
        ).exec()

        if not confirmed:
            return

        new_name, new_color = attributes

        if new_name != name and new_name in self.manager.data:
            notify("This ztrace already exists.")
            return
        
        self.manager.editAttributes(name, new_name, new_color)
    
    def smooth(self):
        """Smooth a set of ztraces."""
        names = self.getSelectedNames()
        if not names:
            return
        
        self.manager.smooth(names)
    
    def addTo3D(self, event=None):
        """Add the ztrace to the 3D scene."""
        names = self.getSelectedNames()
        if not names:
            return
        
        self.manager.addTo3D(names)
    
    def delete(self):
        """Delete a set of ztraces."""
        names = self.getSelectedNames()
        if not names:
            return
        
        self.manager.delete(names)

    # MENU-RELATED FUNCTIONS

    def refresh(self):
        """Refresh the tables."""
        self.manager.refresh()
    
    def export(self):
        """Export the trace list as a csv file."""
        # get the location from the user
        file_path, ext = QFileDialog.getSaveFileName(
            self,
            "Save Ztrace List",
            "ztraces.csv",
            filter="Comma Separated Values (.csv)"
        )
        if not file_path:
            return
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