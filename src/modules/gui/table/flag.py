import re
import os

from PySide6.QtWidgets import (
    QMainWindow, 
    QDockWidget, 
    QTableWidgetItem,  
    QWidget, 
    QInputDialog, 
    QMenu, 
    QFileDialog,
    QAbstractItemView
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt

from .copy_table_widget import CopyTableWidget

from modules.datatypes import Series, Section, Flag
from modules.gui.utils import (
    populateMenuBar,
    populateMenu,
    noUndoWarning,
    notify
)
from modules.gui.dialog import (
    FlagDialog,
    QuickDialog
)
from modules.constants import fd_dir

class FlagTableWidget(QDockWidget):

    def __init__(self, series : Series, mainwindow : QWidget, manager):
        """Create the object table dock widget.
        
            Params:
                series (Series): the Series object
                mainwindow (MainWindow): the main window the dock is connected to
                manager: the object table manager
        """
        # initialize the widget
        super().__init__(mainwindow)
        self.series = series
        self.mainwindow = mainwindow

        # set desired format for widget
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)  # can be docked to right or left side
        self.setWindowTitle("Flag List")

        # set defaults
        self.columns = {
            "Section": True,
            "Title": True,
            "Color": True,
            "Last Comment": True
        }
        self.re_filters = set([".*"])

        # create the main window widget
        self.main_widget = QMainWindow()
        self.setWidget(self.main_widget)
        
        # create the table and the menu
        self.table = None
        self.row_flags = []
        self.createTable()
        self.createMenus()

        # save manager object
        self.manager = manager

        self.show()
    
    def createMenus(self):
        """Create the menu for the object table widget."""
        # Create menubar menu
        menubar_list = [
            {
                "attr_name": "listmenu",
                "text": "List",
                "opts":
                [
                    ("refresh_act", "Refresh", "", self.refresh),
                    ("columns_act", "Set columns...", "", self.setColumns),
                    ("export_act", "Export...", "", self.export),
                    {
                        "attr_name": "filtermenu",
                        "text": "Filter",
                        "opts":
                        [
                            ("refilter_act", "Regex filter...", "", self.setREFilter)
                        ]
                    }
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
            ("editattribtues_act", "Edit attributes...", "", self.editFlag),
            None,
            ("copy_act", "Copy", "", self.table.copy),
            None,
            ("delete_act", "Delete", "", self.deleteFlags)
        ]
        self.context_menu = QMenu(self)
        populateMenu(self, self.context_menu, context_menu_list)
    
    def setRow(self, snum : int, flag : Flag, row : int, resize=True):
        """Set the data for a row of the table.
        
            Params:
                name (str): the name of the object
                row (int): the row to enter this data into
        """
        self.process_check_event = False
        col = 0
        if self.columns["Section"]:
            self.table.setItem(row, col, QTableWidgetItem(str(snum)))
            col += 1
        if self.columns["Title"]:
            self.table.setItem(row, col, QTableWidgetItem(flag.title))
            col += 1
        if self.columns["Color"]:
            item = QTableWidgetItem(" ")
            item.setBackground(QColor(*flag.color))
            self.table.setItem(row, col, item)
            col += 1
        if self.columns["Last Comment"]:
            if flag.comments:
                comment = flag.comments[-1][1]
            else:
                comment = ""
            self.table.setItem(row, col, QTableWidgetItem(comment))
            col += 1
        
        if resize:
            self.table.resizeColumnsToContents()
            self.table.resizeRowToContents(row)
            
    def passesFilters(self, name : str):
        """Check if an object passes the filters.
        
            Params:
                name (str): the name of the object
        """        
        # check regex
        passes_filters = False if self.re_filters else True
        for re_filter in self.re_filters:
            if bool(re.fullmatch(re_filter, name)):
                passes_filters = True
        if not passes_filters:
            return False
        
        return True
    
    def filterFlags(self, section : Section = None):
        """Get the flags that pass the filters."""
        self.passing_flags = []
        for snum, data in self.series.data["sections"].items():
            if section and section.n == snum:
                flags = section.flags
            else:
                flags = data["flags"]
            for flag in flags:
                if self.passesFilters(flag.title):
                    self.passing_flags.append((snum, flag))
        self.passing_flags.sort()
    
    def createTable(self):
        """Create the table widget.
        
            Params:
                objdata (dict): the dictionary containing the object table data objects
        """
        # close an existing table if one exists
        if self.table is not None:
            self.table.close()

        # establish table headers
        self.horizontal_headers = []
        for key, b in self.columns.items():
            if b:
                self.horizontal_headers.append(key)
        
        # filter the objects
        self.filterFlags()

        # create the table object
        self.table = CopyTableWidget(len(self.passing_flags), len(self.horizontal_headers), self.main_widget)
        self.row_flags = [None] * len(self.passing_flags)

        # connect table functions
        self.table.mouseDoubleClickEvent = self.find
        self.table.contextMenuEvent = self.flagContextMenu

        # format table
        # self.table.setWordWrap(False)
        self.table.setShowGrid(False)  # no grid
        self.table.setAlternatingRowColors(True)  # alternate row colors
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # cannot be edited
        self.table.setHorizontalHeaderLabels(self.horizontal_headers)  # titles
        self.table.verticalHeader().hide()  # no veritcal header
        
        # fill in object data
        for r, (snum, flag) in enumerate(self.passing_flags):
            self.setRow(snum, flag, r, resize=False)

        # format rows and columns
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

        # set table as central widget
        self.main_widget.setCentralWidget(self.table)
    
    def updateSection(self, section : Section):
        """Update the flags for a section.
        
            Params:
                section (Section): the section to update
        """
        row, exists_in_table = self.table.getRowIndex(str(section.n))
        while exists_in_table:
            self.table.removeRow(row)
            row, exists_in_table = self.table.getRowIndex(str(section.n))
        
        for flag in sorted(section.flags):
            if self.passesFilters(flag.title):
                self.table.insertRow(row)
                self.setRow(section.n, flag, row)
                row += 1
        
        self.filterFlags()
        print(self.passing_flags)
    
    def resizeEvent(self, event):
        """Resize the table when window is resized."""
        super().resizeEvent(event)
        w = event.size().width()
        h = event.size().height()
        self.table.resize(w, h-20)
    
    def getSelectedFlag(self):
        """Get the name of the object highlighted by the user.
        
            Returns:
                (str): the name of the object
        """
        selected_indexes = self.table.selectedIndexes()
        if len(selected_indexes) != 1:
            return None, None
        return self.passing_flags[selected_indexes[0].row()]
    
    def getSelectedFlags(self):
        """Get the name of the objects highlighted by the user.
        
            Returns:
                (list): the name of the objects
        """
        selected_indexes = self.table.selectedIndexes()
        return [self.passing_flags[i.row()] for i in selected_indexes]

    # RIGHT CLICK FUNCTIONS

    def flagContextMenu(self, event=None):
        """Executed when button is right-clicked: pulls up menu for user to modify objects."""
        if len(self.table.selectedIndexes()) == 0:
            return
        self.context_menu.exec(event.globalPos())
    
    def editFlag(self):
        """Edit a flag."""
        snum, flag = self.getSelectedFlag()
        if not flag:
            notify("Please edit one flag at a time.")
        
        response, confirmed = FlagDialog(self.mainwindow, flag, self.series).exec()
        if not confirmed:
            return
        
        nf = flag.copy()
        nf.title, nf.color, nf.comments = response

        self.manager.editFlag(snum, flag, nf)

    def deleteFlags(self):
        """Delete an object or objects on every section."""
        self.mainwindow.saveAllData()
        selected_flags = self.getSelectedFlags()
        self.manager.deleteFlags(selected_flags)

    # MENU-RELATED FUNCTIONS

    def refresh(self):
        """Refresh the object lists."""
        self.manager.refresh()
    
    def setColumns(self):
        """Set the columns to display."""
        structure = [
            [("check", *tuple(self.columns.items()))]
        ]
        response, confirmed = QuickDialog.get(self, structure, "Table Columns")
        if not confirmed:
            return
        self.columns = dict(response[0])
        
        self.manager.updateTable(self)
    
    def export(self):
        """Export the object list as a csv file."""
        # get the location from the user
        global fd_dir
        file_path, ext = QFileDialog.getSaveFileName(
            self,
            "Save Object List",
            os.path.join(fd_dir.get(), "objects.csv"),
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
        # object data
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
            "Filter Objects",
            "Enter the object filters:",
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
    
    def find(self, event=None):
        """Focus the field on a flag in the series."""
        snum, flag = self.getSelectedFlag()
        if flag is None:
            return
        self.mainwindow.setToFlag(snum, flag)
    
    def closeEvent(self, event):
        """Remove self from manager table list."""
        self.manager.tables.remove(self)
        super().closeEvent(event)

