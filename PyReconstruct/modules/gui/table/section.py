import os

from PySide6.QtWidgets import (
    QTableWidgetItem, 
    QWidget, 
    QInputDialog, 
    QMenu, 
)
from PySide6.QtCore import Qt

from .data_table import DataTable

from PyReconstruct.modules.gui.utils import (
    populateMenuBar,
    populateMenu,
    noUndoWarning,
    notify
)
from PyReconstruct.modules.gui.dialog import QuickDialog, FileDialog
from PyReconstruct.modules.datatypes import Series

class SectionTableWidget(DataTable):

    def __init__(self, series : Series, mainwindow : QWidget, manager):
        """Create the trace table dock widget.
        
            Params:
                series (Series): the series object
                mainwindow (QWidget): the main window the dock is connected to
                manager: the trace table manager
        """
        super().__init__("section", series, mainwindow, manager)
        self.static_columns = ["Section"]
        self.createTable()

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
                    ("refresh_act", "Refresh", "", self.refresh),
                    ("columns_act", "Set columns...", "", self.setColumns),
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
        self.menubar.clear()
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
    
    def getFiltered(self):
        return sorted(list(self.series.sections.keys()))
    
    def getItems(self, snum : int, item_type : str):
        """Get the QTableWidgetItem(s) for an attribute of a section.
        
            Params:
                snum (int): the section nubmer to retrieve the data for
                item_type (str): the specific data to be retrieved
        """
        section_data = self.series.data["sections"][snum]
        items = []

        if item_type == "Section":
            s = str(snum)
            if section_data["calgrid"]: s += " (calgrid)"
            items.append(QTableWidgetItem(s))
        elif item_type == "Thickness":
            items.append(QTableWidgetItem(
                str(round(section_data["thickness"], 5))
            ))
        elif item_type == "Locked":
            item = QTableWidgetItem("")
            item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            item.setCheckState(Qt.CheckState.Checked if section_data["locked"] else Qt.CheckState.Unchecked)
            items.append(item)
        elif item_type == "Brightness":
            brightness, contrast = section_data["bc_profiles"][self.series.bc_profile]
            items.append(QTableWidgetItem(
                str(brightness)
            ))
        elif item_type == "Contrast":
            brightness, contrast = section_data["bc_profiles"][self.series.bc_profile]
            items.append(QTableWidgetItem(
                str(contrast)
            ))
        elif item_type == "Image Source":
            items.append(QTableWidgetItem(
                str(section_data["src"])
            ))
        return items
    
    def updateData(self, snum : int):
        """Update the tables for a single section.
        
            Params:
                snum (int): the section number to update
        """
        # iterate through rows to find section number
        for r in range(self.table.rowCount()):
            t = self.table.item(r, 0).text()
            t = t.split()[0]
            if int(t) == snum:
                self.setRow(snum, r)
    
    def getSelected(self, single=False):
        """Get the sections that are selected by the user.
        
            Params:
                single (bool): True if only one section should be selected
        """
        selected_indeces = self.table.selectedIndexes()
        if len(selected_indeces) < 1:
            return
        n_list = []
        for i in selected_indeces:
            text = self.table.item(i.row(), 0).text()
            n = int(text.split()[0])
            n_list.append(n)
        
        if single:
            if len(n_list) != 1:
                notify("Please select only one section for this option.")
                return
            else:
                return n_list[0]
        else:
            return n_list
    
    def itemChanged(self, item : QTableWidgetItem):
        """User checked a lock checkbox."""
        if not self.process_check_event:
            return
        snum = int(self.table.item(item.row(), 0).text())
        lock = item.checkState() == Qt.CheckState.Checked
        self.lockSections(lock, section_numbers=[snum])
    
    def mouseDoubleClickEvent(self, event=None):
        """Find the section when double-clicked."""
        super().mouseDoubleClickEvent(event)
        self.findSection()

    # RIGHT CLICK FUNCTIONS

    def lockSections(self, lock=True, section_numbers=None, log_event=True):
        """Lock or unlock a set of sections.
        
            Params:
                lock (bool): True if section should be locked
                section_numbers (list): the list of sections to modify
        """
        if section_numbers is None:
            section_numbers = self.getSelected()
        if not section_numbers:
            return
        
        self.mainwindow.saveAllData()

        for snum in section_numbers:
            section = self.series.loadSection(snum)
            section.align_locked = lock
            section.save()
            if log_event:
                self.series.addLog(None, snum, f"{'Lock' if lock else 'Unlock'} section")
        
        self.manager.updateSections(section_numbers)
        
        # update the field
        self.mainwindow.field.reload()
        self.mainwindow.seriesModified(True)
    
    def setBC(self, section_numbers=None, b=None, c=None, inc=False, log_event=True):
        """Set the brightness/contrast for a set of sections."""
        if section_numbers is None:
            section_numbers = self.getSelected()
            if not section_numbers:
                return
        
        for snum in section_numbers:
            if self.series.data["sections"][snum]["locked"]:
                notify("Unlock section(s) before modifying.")
                return
        
        if b is None or c is None:
            desc = "increment" if inc else "(-100 - 100)"

            structure = [
                [f"Brightness {desc}:", ("int", None, tuple(range(-100, 101)))],
                [f"Contrast {desc}:", ("int", None, tuple(range(-100, 100)))]
            ]
            response, confirmed = QuickDialog.get(self, structure, "Brightness/Contrast")
            if not confirmed:
                return
            
            b, c = tuple(response)

        self.mainwindow.saveAllData()

        for snum in section_numbers:
            section = self.series.loadSection(snum)
            if b is not None:
                if inc:
                    section.brightness += b
                else:
                    section.brightness = b
                section.brightness = max(-100, min(100, section.brightness))
            if c is not None:
                if inc:
                    section.contrast += c
                else:
                    section.contrast = c
                section.contrast = max(-100, min(100, section.contrast))
            section.save()
            if log_event:
                self.series.addLog(None, snum, "Modify brightness/contrast")
        
        self.manager.updateSections(section_numbers)
        
        # update the field
        self.mainwindow.field.reload()
        self.mainwindow.seriesModified(True)
    
    def matchBC(self):
        """Match the brightness/contrast of the selected sections with the current section."""
        section_numbers = self.getSelected()
        if not section_numbers:
            return
        
        for snum in section_numbers:
            if self.series.data["sections"][snum]["locked"]:
                notify("Unlock section(s) before modifying.")
                return
        
        b = self.mainwindow.field.section.brightness
        c = self.mainwindow.field.section.contrast
        self.setBC(section_numbers, b, c)
    
    def optimizeBC(self):
        """Optimize the brightness/contrast of the selected sections."""
        section_numbers = self.getSelected()
        if not section_numbers:
            return
        
        for snum in section_numbers:
            if self.series.data["sections"][snum]["locked"]:
                notify("Unlock section(s) before modifying.")
                return
        
        self.mainwindow.optimizeBC(section_numbers)
    
    def editThickness(self, log_event=True):
        """Modify the section thickness for a set of sections."""
        section_numbers = self.getSelected()
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
            thickness = float(new_st)
        except ValueError:
            return
        
        self.mainwindow.saveAllData()

        # keep track of which objects to update
        modified_contours = set()

        # iterate through selected sections
        for snum in section_numbers:
            section = self.series.loadSection(snum)
            section.thickness = thickness
            # flag all traces as modified because the thickness of the section has been changed
            section.modified_contours = set(section.contours.keys())
            modified_contours.union(section.modified_contours)
            section.save()
            self.manager.updateObjects(section.modified_contours)
            if log_event:
                self.series.addLog(None, snum, f"Change section thickness to {thickness}")
                
        self.manager.updateSections(section_numbers)
        self.manager.updateObjects(modified_contours)
        self.manager.updateZtraces(set(self.series.ztraces.keys()))  # update all of the ztrace distances

        self.mainwindow.field.reload()
        self.mainwindow.seriesModified(True)
            
    def editSrc(self, log_event=True):
        """Modify the image source for a single section."""
        snum = self.getSelected(single=True)
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
        
        self.mainwindow.saveAllData()

        section = self.series.loadSection(snum)
        section.src = new_src
        section.save()
        
        if log_event:
            self.series.addLog(None, snum, f"Change section image source to {new_src}")

        self.mainwindow.field.reload()
        self.mainwindow.field.reloadImage()

        self.manager.updateSections([snum])
        self.mainwindow.seriesModified(True)
    
    def deleteSections(self):
        """Delete the sections selected by the user."""
        section_numbers = self.getSelected()
        if not section_numbers:
            return
        
        for snum in section_numbers:
            if self.series.data["sections"][snum]["locked"]:
                notify("Cannot delete locked sections.")
                return
        
        if not noUndoWarning():
            return
        
        self.mainwindow.saveAllData()
        
        self.series.deleteSections(section_numbers)

        # clear the states
        self.mainwindow.field.clearStates()
        
        # switch to first section if current section is deleted
        if self.series.current_section in section_numbers:
            self.mainwindow.changeSection(sorted(list(self.series.sections.keys()))[0], save=False)
        
        # refresh the data in all tables
        self.manager.recreateTables(refresh_data=True)

        self.mainwindow.seriesModified(True)
    
    def backspace(self):
        """Delete the sections."""
        self.deleteSections()
    
    def findSection(self, event=None):
        """Find the section selected by the user."""
        snum = self.getSelected(single=True)
        if snum is None:
            return
        
        self.mainwindow.changeSection(snum)
    
    def sectionContextMenu(self, event=None):
        """Executed when button is right-clicked: pulls up menu for user to modify traces."""
        if len(self.table.selectedIndexes()) == 0:
            return
        self.context_menu.exec(event.globalPos())

    # MENU-RELATED FUNCTIONS
    
    def modifyAllSrc(self, log_event=True):
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
        
        # edit all sections 
        s = new_src.split("#")
        if len(s) != 2:
            return
        max_digits = len(str(max(self.series.sections.keys())))
        for snum, section in self.series.enumerateSections(message="Modifying section image sources..."):
            section_src = s[0] + str(snum).zfill(max_digits) + s[1]
            section.src = section_src
            section.save()
    
        if log_event:
            self.series.addLog(None, snum, f"Change section image source to {new_src}")

        self.mainwindow.field.reload()
        self.mainwindow.field.reloadImage()

        self.manager.updateSections(list(self.series.sections.keys()))
        self.mainwindow.seriesModified(True)
    
    def reorderSections(self):
        """Reorder the sections so that they are in order."""
        # check to make sure all sections are unlocked
        for snum in self.series.sections:
            if self.series.data["sections"][snum]["locked"]:
                notify("Unlock section(s) before modifying.")
                return
            
        if not noUndoWarning():
            return
        
        self.mainwindow.saveAllData()

        d = dict(tuple((snum, i) for i, snum in enumerate(self.series.sections.keys())))
        self.series.reorderSections(d)
        self.series.addLog(None, None, "Reorder sections")
        
        # refresh all table data
        self.manager.recreateTables(refresh_data=True)
        
        # clear the states
        self.mainwindow.field.clearStates()
        self.manager.refresh()
        self.mainwindow.field.reload()
    
    def insertSection(self, before=True):
        """Insert a section into the series."""
        if before:
            index = min(self.getSelected())
        else:
            index = max(self.getSelected()) + 1
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
        if not src:
            src = "no-image"
        else:
            src = os.path.basename(src)

        self.mainwindow.saveAllData()
        
        self.series.insertSection(
            index,
            src,
            mag,
            thickness
        )
        self.series.addLog(None, index, "Insert section")

        # refresh the data for all tables
        self.manager.recreateTables(refresh_data=True)
        
        # clear the field section states
        self.mainwindow.field.clearStates()
        self.manager.refresh()
        self.mainwindow.field.reload()
