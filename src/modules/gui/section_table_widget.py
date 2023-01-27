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

from modules.gui.gui_functions import (
    populateMenuBar,
    populateMenu,
    noUndoWarning
)
from modules.gui.dialog import (
    BCDialog
)

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
            {
                "attr_name": "bcmenu",
                "text": "Brightness/contrast",
                "opts":
                [
                    ("setbc_act", "Set brightness/contrast", "", self.setBC),
                    ("matchbc_act", "Match brightness/contrast to current section", "", self.matchBC)
                ]
            },
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
    
    def setRow(self, r : int, snum : int, section_data : dict):
        """Set the data for a row.
        
            Params:
                r (int): the row index
                snum (int): the section number
                section_data (dict): the data for the section
        """
        self.table.setItem(r, 0, QTableWidgetItem(
            str(snum) + (" (calgrid)" if section_data["calgrid"] else "")
        ))
        self.table.setItem(r, 1, QTableWidgetItem(
            str(round(section_data["thickness"], 5))
        ))
        self.table.setItem(r, 2, QTableWidgetItem(
            "Locked" if section_data["align_locked"] else "Unlocked"
        ))
        self.table.setItem(r, 3, QTableWidgetItem(
            str(section_data["brightness"])
        ))
        self.table.setItem(r, 4, QTableWidgetItem(
            str(section_data["contrast"])
        ))
    
    def createTable(self, sectiondict : dict):
        """Create the table widget.
        
            Params:
                sectiondict (dict): section number : (thickness, locked)
        """
        self.sectiondict = sectiondict
        self.table = QTableWidget(len(sectiondict), 5)

        # connect table functions
        self.table.contextMenuEvent = self.sectionContextMenu
        self.table.mouseDoubleClickEvent = self.findSection

        # establish table headers
        self.horizontal_headers = ["Section", "Thickness", "Locked", "Brightness", "Contrast"]

        # format table
        self.table.setShowGrid(False)  # no grid
        self.table.setAlternatingRowColors(True)  # alternate row colors
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # cannot be edited
        self.table.setHorizontalHeaderLabels(self.horizontal_headers)  # titles
        self.table.verticalHeader().hide()  # no veritcal header
        
        # fill in section data
        r = 0
        for snum in sorted(sectiondict.keys()):
            self.setRow(r, snum, sectiondict[snum])
            r += 1

        self.format()

        # set table as central widget
        self.main_widget.setCentralWidget(self.table)
    
    def updateSection(self, snum : int, section_data : dict):
        """Update the tables for a single section.
        
            Params:
                snum (int): the section number to update
                sectiondict (dict): the data for the section
        """

        # iterate through rows to find section number
        for r in range(self.table.rowCount()):
            t = self.table.item(r, 0).text()
            t = t.split()[0]
            if int(t) == snum:
                self.setRow(r, snum, section_data)

    
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
    
    def setBC(self):
        """Set the brightness/contrast for a set of sections."""
        section_numbers = self.getSelectedSections()
        if not section_numbers:
            return
        
        (b, c), confirmed = BCDialog(self).exec()
        if not confirmed:
            return
        
        if b is not None and c is not None:
            self.manager.setBC(section_numbers, b, c)
    
    def matchBC(self):
        """Match the brightness/contrast of the selected sections with the current section."""
        section_numbers = self.getSelectedSections()
        if not section_numbers:
            return
        
        self.manager.matchBC(section_numbers)
    
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
        
        if not noUndoWarning():
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