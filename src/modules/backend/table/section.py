import os

from PySide6.QtCore import Qt

from modules.gui.table import SectionTableWidget
from modules.datatypes import Series

class SectionTableManager():

    def __init__(self, series : Series, mainwindow):
        """Create the trace table manager.
        
            Params:
                series (Series): the series object
                mainwindow (MainWindow): the main window widget
        """
        self.tables = []
        self.series = series
        self.mainwindow = mainwindow
        self.loadSections()

    def loadSections(self):
        """Load all of the data for each section in the series."""
        self.data = {}
        for snum, section in self.series.enumerateSections(
            message="Loading section data..."
        ):
            self.data[snum] = {
                "thickness": section.thickness,
                "align_locked": section.align_locked,
                "calgrid": section.calgrid,
                "brightness": section.brightness,
                "contrast": section.contrast
            }

        # add the data to the tables
        for table in self.tables:
            table.createTable(self.data)
    
    def newTable(self):
        """Create a new trace list."""
        new_table = SectionTableWidget(
            self.data,
            self.mainwindow,
            self
        )
        self.tables.append(new_table)
        self.mainwindow.addDockWidget(Qt.LeftDockWidgetArea, new_table)

    # MENU-RELATED FUNCTIONS
    
    def updateTables(self):
        """Updates a table with the current data.
        
            Params:
                table (ObjectTableWidget): the table to update
        """
        for table in self.tables:
            table.createTable(self.data)
    
    def updateSection(self, section):
        """Update the data for a section.
        
            Params:
                section (Section): the section with data to update
        """
        self.data[section.n] = {
            "thickness": section.thickness,
            "align_locked": section.align_locked,
            "calgrid": section.calgrid,
            "brightness": section.brightness,
            "contrast": section.contrast
        }
        for table in self.tables:
            table.updateSection(section.n, self.data[section.n])
    
    def lockSections(self, section_numbers : list[int], lock : bool):
        """Lock or unlock a set of sections.
        
            Params:
                section_numbers (list): the list of section numbers to modify
                lock (bool): True if sections should be locked
        """
        self.mainwindow.saveAllData()

        for snum in section_numbers:
            section = self.series.loadSection(snum)
            section.align_locked = lock
            section.save()
            # update the table data
            self.data[snum]["align_locked"] = lock
        
        # update the field
        self.mainwindow.field.reload()
        self.mainwindow.seriesModified(True)

        # update the tables
        self.updateTables()

    def setBC(self, section_numbers : list[int], b : int, c : int):
        """Set the brightness and contrast for a set of sections.
        
            Params:
                section_numbers (list): the list of section numbers to set
                b (int): the brightness to set
                c (int): the contrast to set
        """
        self.mainwindow.saveAllData()

        for snum in section_numbers:
            section = self.series.loadSection(snum)
            if b is not None:
                section.brightness = b
            if c is not None:
                section.contrast = c
            section.save()
            # update table data
            self.data[snum]["brightness"] = b
            self.data[snum]["contrast"] = c
        
        # update the field
        self.mainwindow.field.reload()
        self.mainwindow.seriesModified(True)

        # update the tables
        self.updateTables()
    
    def matchBC(self, section_numbers : list[int]):
        """Match the brightness and contrast of a set of sections to the current section.
        
            Params:
                section_numbers (list): the sections to modify
        """
        b = self.data[self.series.current_section]["brightness"]
        c = self.data[self.series.current_section]["contrast"]
        self.setBC(section_numbers, b, c)

    def editThickness(self, section_numbers : list[int], thickness : float):
        """Set the section thickness for a set of sections.
        
            Params:
                section_numbers (list): the list of section numbers to modify
                thickness (float): the new thickness to set for the sections
        """
        self.mainwindow.saveAllData()

        for snum in section_numbers:
            section = self.series.loadSection(snum)
            section.thickness = thickness
            section.save()
            # update the table data
            self.data[snum]["thickness"] = thickness
        
        self.mainwindow.field.reload()
        self.updateTables()

        # refresh any existing obj table
        if self.mainwindow.field.obj_table_manager:
            self.mainwindow.field.obj_table_manager.refresh()
        
        self.mainwindow.seriesModified(True)
    
    def deleteSections(self, section_numbers : list[int]):
        """Delete a set of sections.
        
            Params:
                section_numbers (list): the list of sections to delete
        """
        self.mainwindow.saveAllData()
        
        for snum in section_numbers:
            # delete the file
            filename = self.series.sections[snum]
            os.remove(os.path.join(self.series.getwdir(), filename))
            # delete link to file
            del(self.series.sections[snum])
            del(self.data[snum])
        
        # switch to first section if current section is deleted
        if self.series.current_section in section_numbers:
            self.mainwindow.changeSection(sorted(list(self.series.sections.keys()))[0], save=False)
        
        self.updateTables()

        self.mainwindow.seriesModified(True)
            
    def findSection(self, section_number : int):
        """Focus the view on a specific section.
        
            Params:
                section_number (int): the section the focus on
        """
        self.mainwindow.changeSection(section_number)
        
    def close(self):
        """Close all tables."""
        for table in self.tables:
            table.close()


