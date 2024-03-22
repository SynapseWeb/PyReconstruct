import os

from PySide6.QtWidgets import (
    QMainWindow, 
    QDockWidget, 
    QTableWidgetItem, 
    QAbstractItemView, 
    QWidget, 
    QInputDialog, 
    QMenu, 
)
from PySide6.QtCore import Qt

from .copy_table_widget import CopyTableWidget

from PyReconstruct.modules.gui.utils import (
    populateMenuBar,
    populateMenu,
    noUndoWarning,
    notify
)
from PyReconstruct.modules.gui.dialog import QuickDialog, FileDialog
from PyReconstruct.modules.datatypes import Series

class SectionTableWidget(QDockWidget):

    def __init__(self, series : Series, mainwindow : QWidget, manager):
        """Create the trace table dock widget.
        
            Params:
                series (Series): the series object
                mainwindow (QWidget): the main window the dock is connected to
                manager: the trace table manager
        """
        # initialize the widget
        super().__init__(mainwindow)
        self.mainwindow = mainwindow

        self.series = series

        # set desired format for widget
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)  # ccan be docked to right or left side
        self.setWindowTitle("Section List")

        # create the main window widget
        self.main_widget = QMainWindow()
        self.setWidget(self.main_widget)
        
        # create the table and the menu
        self.table = None
        self.process_check_event = True
        self.createTable()
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
            },
            {
                "attr_name": "modifymenu",
                "text": "Modify",
                "opts":
                [
                    ("modifyallsrc_act", "Section image sources...", "", self.modifyAllSrc),
                    ("reordersections_act", "Reorder sections", "", self.reorderSections)
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
                    ("setbc_act", "Set...", "", self.setBC),
                    ("incbc_acrt", "Increment...", "", lambda : self.setBC(inc=True)),
                    ("matchbc_act", "Match values to section in view", "", self.matchBC),
                    ("optimizebc_act", "Optimize...", "", self.optimizeBC),
                ]
            },
            ("thickness_act", "Edit thickness...", "", self.editThickness),
            ("editsrc_act", "Edit image source...", "", self.editSrc),
            {
                "attr_name": "insertmenu",
                "text": "Insert",
                "opts":
                [
                    ("insertabove_act", "Above", "", self.insertSection),
                    ("insertbelow_act", "Below", "", lambda : self.insertSection(False))
                ]
            },
            None,
            ("copy_act", "Copy", "", self.table.copy),
            None,
            ("delete_act", "Delete", "", self.deleteSections)
        ]
        self.context_menu = QMenu(self)
        populateMenu(self, self.context_menu, context_menu_list)
    
    def format(self):
        """Format the rows and columns of the table."""
        self.table.resizeRowsToContents()
        self.table.resizeColumnsToContents()
    
    def setRow(self, r : int, snum : int):
        """Set the data for a row.
        
            Params:
                r (int): the row index
                snum (int): the section number
        """
        self.process_check_event = False
        section_data = self.series.data["sections"][snum]

        self.table.setItem(r, 0, QTableWidgetItem(
            str(snum) + (" (calgrid)" if section_data["calgrid"] else "")
        ))
        self.table.setItem(r, 1, QTableWidgetItem(
            str(round(section_data["thickness"], 5))
        ))

        # checkbox for locked/unlocked
        item = QTableWidgetItem("")
        item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
        item.setCheckState(Qt.CheckState.Checked if section_data["locked"] else Qt.CheckState.Unchecked)
        self.table.setItem(r, 2, item)

        brightness, contrast = section_data["bc_profiles"][self.series.bc_profile]
        self.table.setItem(r, 3, QTableWidgetItem(
            str(brightness)
        ))
        self.table.setItem(r, 4, QTableWidgetItem(
            str(contrast)
        ))
        self.table.setItem(r, 5, QTableWidgetItem(
            str(section_data["src"])
        ))
        self.process_check_event = True
    
    def createTable(self):
        """Create the table widget."""
        # close an existing table and save scroll position
        if self.table is not None:
            vscroll = self.table.verticalScrollBar()
            scroll_pos = vscroll.value()
            self.table.close()
        else:
            scroll_pos = 0
        
        # establish table headers
        self.horizontal_headers = ["Section", "Thickness", "Locked", "Brightness", "Contrast", "Image Source"]

        self.table = CopyTableWidget(len(self.series.sections), len(self.horizontal_headers))

        # connect table functions
        self.table.contextMenuEvent = self.sectionContextMenu
        self.table.mouseDoubleClickEvent = self.findSection
        self.table.backspace = self.deleteSections

        # format table
        self.table.setShowGrid(False)  # no grid
        self.table.setAlternatingRowColors(True)  # alternate row colors
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # cannot be edited
        self.table.setHorizontalHeaderLabels(self.horizontal_headers)  # titles
        self.table.verticalHeader().hide()  # no veritcal header
        
        # fill in section data
        r = 0
        for snum in sorted(self.series.sections.keys()):
            self.setRow(r, snum)
            r += 1

        self.format()

        # set the saved scroll value
        self.table.verticalScrollBar().setValue(scroll_pos)

        # set table as central widget
        self.main_widget.setCentralWidget(self.table)

        # connect checkbox functions
        self.table.itemChanged.connect(self.checkLock)
    
    def updateSection(self, snum : int):
        """Update the tables for a single section.
        
            Params:
                snum (int): the section number to update
        """
        # iterate through rows to find section number
        for r in range(self.table.rowCount()):
            t = self.table.item(r, 0).text()
            t = t.split()[0]
            if int(t) == snum:
                self.setRow(r, snum)
    
    def getSelectedSection(self):
        """Get the section that is selected by the user."""
        selected_indeces = self.table.selectedIndexes()
        if len(selected_indeces) != 1:
            return
        text = self.table.item(selected_indeces[0].row(), 0).text()
        n = int(text.split()[0])  # check for calgrid text
        return n
    
    def getSelectedSections(self):
        """Get the trace items that iare selected by the user."""
        selected_indeces = self.table.selectedIndexes()
        if len(selected_indeces) < 1:
            return
        n_list = []
        for i in selected_indeces:
            text = self.table.item(i.row(), 0).text()
            n = int(text.split()[0])
            n_list.append(n)
        return n_list
    
    def resizeEvent(self, event):
        """Resize the table when window is resized."""
        super().resizeEvent(event)
        w = event.size().width()
        h = event.size().height()
        self.table.resize(w, h-20)
    
    def checkLock(self, item : QTableWidgetItem):
        """User checked a lock checkbox."""
        if not self.process_check_event:
            return
        snum = int(self.table.item(item.row(), 0).text())
        lock = item.checkState() == Qt.CheckState.Checked
        self.lockSections(lock, section_numbers=[snum])

    # RIGHT CLICK FUNCTIONS

    def lockSections(self, lock=True, section_numbers=None):
        """Lock or unlock a set of sections.
        
            Params:
                lock (bool): True if section should be locked
                section_numbers (list): the list of sections to modify
        """
        if section_numbers is None:
            section_numbers = self.getSelectedSections()
        if not section_numbers:
            return
        self.manager.lockSections(section_numbers, lock)
    
    def setBC(self, inc=False):
        """Set the brightness/contrast for a set of sections."""
        section_numbers = self.getSelectedSections()
        if not section_numbers:
            return
        
        for snum in section_numbers:
            if self.series.data["sections"][snum]["locked"]:
                notify("Unlock section(s) before modifying.")
                return
        
        desc = "increment" if inc else "(-100 - 100)"

        structure = [
            [f"Brightness {desc}:", ("int", None, tuple(range(-100, 101)))],
            [f"Contrast {desc}:", ("int", None, tuple(range(-100, 100)))]
        ]
        response, confirmed = QuickDialog.get(self, structure, "Brightness/Contrast")
        if not confirmed:
            return

        self.manager.setBC(section_numbers, *response, inc=inc)
    
    def matchBC(self):
        """Match the brightness/contrast of the selected sections with the current section."""
        section_numbers = self.getSelectedSections()
        if not section_numbers:
            return
        
        for snum in section_numbers:
            if self.series.data["sections"][snum]["locked"]:
                notify("Unlock section(s) before modifying.")
                return
        
        self.manager.matchBC(section_numbers)
    
    def optimizeBC(self):
        """Optimize the brightness/contrast of the selected sections."""
        section_numbers = self.getSelectedSections()
        if not section_numbers:
            return
        
        for snum in section_numbers:
            if self.series.data["sections"][snum]["locked"]:
                notify("Unlock section(s) before modifying.")
                return
        
        self.mainwindow.optimizeBC(section_numbers)
    
    def editThickness(self):
        """Modify the section thickness for a set of sections."""
        section_numbers = self.getSelectedSections()
        if not section_numbers:
            return
        
        for snum in section_numbers:
            if self.series.data["sections"][snum]["locked"]:
                notify("Unlock section(s) before modifying.")
                return
        
        # get the existing section thickness
        snum = section_numbers[0]
        sthickness = self.series.data["sections"][snum]["thickness"]
        for snum in section_numbers[1:]:
            if self.series.data["sections"][snum]["thickness"] != sthickness:
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
        if not confirmed:
            return

        try:
            new_st = float(new_st)
        except ValueError:
            return
        
        self.manager.editThickness(section_numbers, new_st)
    
    def editSrc(self):
        """Modify the image source for a single section."""
        snum = self.getSelectedSection()
        if snum is None:
            return

        if self.series.data["sections"][snum]["locked"]:
            notify("Unlock section(s) before modifying.")
            return

        # get the existing section source
        src = self.series.data["sections"][snum]["src"]

        # get the new image source from the user
        new_src, confirmed = QInputDialog.getText(
            self,
            "Image source",
            "Enter image source:",
            text=src
        )
        if not confirmed:
            return
        
        self.manager.editSrc(snum, new_src)
    
    def deleteSections(self):
        """Delete the sections selected by the user."""
        section_numbers = self.getSelectedSections()
        if not section_numbers:
            return
        
        for snum in section_numbers:
            if self.series.data["sections"][snum]["locked"]:
                notify("Cannot delete locked sections.")
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
        file_path = FileDialog.get(
            "save",
            self,
            "Save Section List",
            file_name="sections.csv",
            filter="Comma Separated Values (*.csv)"
        )
        if not file_path: return
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
    
    def modifyAllSrc(self):
        """Modify the image source for all sections."""
        # check to ensure all sections are unlocked
        for snum in self.series.sections:
            if self.series.data["sections"][snum]["locked"]:
                notify("Unlock section(s) before modifying.")
                return
            
        # attempt to use the last section src as an example
        snum = max(self.series.sections.keys())
        example_src = self.series.data["sections"][snum]["src"]
        if str(snum) in example_src:
            example_src = example_src.replace(str(snum), "#", 1)
        else:
            example_src = ""
        
        # get the new source name from the user
        new_src = ""
        while new_src.count("#") != 1:
            new_src, confirmed = QInputDialog.getText(
                self,
                "Rename Image Sources",
                "New image source name\n(use a single '#' symbol to represent the section number)",
                text=example_src
            )
            if not confirmed:
                return
            c = new_src.count("#")
            if c == 0:
                notify("Please use a '#' symbol to represent the section number.")
            elif c > 1:
                notify("Please use only one '#' symbol to represent the section number.")
        
        self.manager.editSrc(None, new_src)
    
    def reorderSections(self):
        """Reorder the sections so that they are in order."""
        # check to make sure all sections are unlocked
        for snum in self.series.sections:
            if self.series.data["sections"][snum]["locked"]:
                notify("Unlock section(s) before modifying.")
                return
            
        if not noUndoWarning():
            return
        
        self.manager.reorderSections()
    
    def insertSection(self, before=True):
        """Insert a section into the series."""
        if before:
            index = min(self.getSelectedSections())
        else:
            index = max(self.getSelectedSections()) + 1
        structure = [
            ["Image:", ("file", "", "*.jpg *.jpeg *.png *.tif *.tiff *.bmp")],
            ["Section number:", ("int", index)],
            ["Calibration (μm/px):", ("float", self.mainwindow.field.section.mag)],
            ["Thickness (μm):", ("float", self.mainwindow.field.section.thickness)]
        ]
        response, confirmed = QuickDialog.get(self, structure, "Create Section")
        if not confirmed:
            return
        
        src, index, mag, thickness = response
        src = os.path.basename(src)

        self.manager.insertSection(index, src, mag, thickness)

    def closeEvent(self, event):
        """Remove self from manager table list."""
        self.manager.tables.remove(self)
        super().closeEvent(event)
