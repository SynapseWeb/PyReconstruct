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
    QFileDialog
)
from PySide6.QtCore import Qt

from modules.gui.gui_functions import populateMenuBar, populateMenu

class SectionTableWidget(QDockWidget):

    def __init__(self, sectiondict : dict, mainwindow : QWidget, manager):
        """Create the trace table dock widget.
        
            Params:
                series (Series): the series object
                sectiondict (dict): contains all section info for the table
                mainwindow (QWidget): the main window the dock is connected to
                manager: the trace table manager
        """
        # initialize the widget
        super().__init__(mainwindow)
        self.mainwindow = mainwindow

        # set desired format for widget
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)  # ccan be docked to right or left side
        self.setWindowTitle("Section List")

        # create the main window widget
        self.main_widget = QMainWindow()
        self.setWidget(self.main_widget)
        
        # create the table and the menu
        self.table = None
        self.createTable(sectiondict)
        self.createMenus()

        # save manager object
        self.manager = manager

        self.show()
    
    def createMenus(self):
        """Create the menu for the trace table widget."""
        # Create menubar menu
        menubar_list = [
            {
                "attr_name": "listmenu",
                "text": "List",
                "opts":
                [
                    ("export_act", "Export...", "", self.export),
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
            ("lock_act", "Lock sections", "", self.lockSections),
            ("unlock_act", "Unlock sections", "", lambda : self.lockSections(False)),
            None,
            ("thickness_act", "Edit thickness...", "", self.editThickness),
            None,
            ("delete_act", "Delete", "", self.deleteSections)
        ]
        self.context_menu = QMenu(self)
        populateMenu(self, self.context_menu, context_menu_list)
    
    def format(self):
        """Format the rows and columns of the table."""
        self.table.resizeRowsToContents()
        self.table.resizeColumnsToContents()
    
    def createTable(self, sectiondict : dict):
        """Create the table widget.
        
            Params:
                sectiondict (dict): section number : (thickness, locked)
        """
        self.sectiondict = sectiondict
        self.table = QTableWidget(len(sectiondict), 3)

        # connect table functions
        self.table.contextMenuEvent = self.sectionContextMenu
        self.table.mouseDoubleClickEvent = self.findSection

        # establish table headers
        self.horizontal_headers = ["Section", "Thickness", "Locked"]

        # format table
        self.table.setShowGrid(False)  # no grid
        self.table.setAlternatingRowColors(True)  # alternate row colors
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # cannot be edited
        self.table.setHorizontalHeaderLabels(self.horizontal_headers)  # titles
        self.table.verticalHeader().hide()  # no veritcal header
        
        # fill in section data
        r = 0
        for snum in sorted(sectiondict.keys()):
            self.table.setItem(r, 0, QTableWidgetItem(str(snum)))
            thickness, locked = sectiondict[snum]
            self.table.setItem(r, 1, QTableWidgetItem(str(round(thickness, 5))))
            if locked:
                locked_str = "Locked"
            else:
                locked_str = "Unlocked"
            self.table.setItem(r, 2, QTableWidgetItem(str(locked_str)))
            r += 1

        self.format()

        # set table as central widget
        self.main_widget.setCentralWidget(self.table)
    
    def getSelectedSection(self):
        """Get the section that is selected by the user."""
        selected_indeces = self.table.selectedIndexes()
        if len(selected_indeces) != 1:
            return
        return int(self.table.item(selected_indeces[0].row(), 0).text())
    
    def getSelectedSections(self):
        """Get the trace items that iare selected by the user."""
        selected_indeces = self.table.selectedIndexes()
        if len(selected_indeces) < 1:
            return
        return [
            int(self.table.item(i.row(), 0).text()) for i in selected_indeces
        ]    
    
    def resizeEvent(self, event):
        """Resize the table when window is resized."""
        super().resizeEvent(event)
        w = event.size().width()
        h = event.size().height()
        self.table.resize(w, h-20)

    # RIGHT CLICK FUNCTIONS

    def lockSections(self, lock=True):
        """Lock or unlock a set of sections."""
        section_numbers = self.getSelectedSections()
        if not section_numbers:
            return
        self.manager.lockSections(section_numbers, lock)
    
    def editThickness(self):
        """Modify the section thickness for a set of sections."""
        section_numbers = self.getSelectedSections()
        if not section_numbers:
            return
        
        # get the existing section thickness
        snum = section_numbers[0]
        sthickness = self.sectiondict[snum][0]
        for snum in section_numbers[1:]:
            if self.sectiondict[snum][0] != sthickness:
                sthickness = 0
                break
        if sthickness:
            sthickness = str(sthickness)
        else:
            sthickness = ""

        # get the new section thickness from the user
        new_st, confirmed = QInputDialog.getText(
            self,
            "Section Thickness",
            "Enter section thickness (microns):",
            text=sthickness
        )

        try:
            new_st = float(new_st)
        except ValueError:
            return
        
        self.manager.editThickness(section_numbers, new_st)
    
    def deleteSections(self):
        """Delete the sections selected by the user."""
        section_numbers = self.getSelectedSections()
        if not section_numbers:
            return
        
        self.manager.deleteSections(section_numbers)
    
    def findSection(self, event):
        """Find the section selected by the user."""
        snum = self.getSelectedSection()
        if snum is None:
            return
        
        self.manager.findSection(snum)
    
    def sectionContextMenu(self, event=None):
        """Executed when button is right-clicked: pulls up menu for user to modify traces."""
        if len(self.table.selectedIndexes()) == 0:
            return
        self.context_menu.exec(event.globalPos())

    # MENU-RELATED FUNCTIONS
    
    def export(self):
        """Export the trace list as a csv file."""
        # get the location from the user
        file_path, ext = QFileDialog.getSaveFileName(
            self,
            "Save Trace List",
            "traces.csv",
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