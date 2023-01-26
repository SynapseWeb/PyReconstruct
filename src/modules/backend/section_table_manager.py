import os

from PySide6.QtCore import Qt

from modules.gui.section_table_widget import SectionTableWidget

from modules.pyrecon.series import Series

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
            section = self.series.loadSection(snum)
            self.data[snum] = (
                section.thickness,
                section.align_locked,
                section.calgrid
            )

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
            thickness, old_lock = self.data[snum]
            self.data[snum] = thickness, lock
        
        # update the field
        self.mainwindow.field.reload()
        self.mainwindow.seriesModified(True)

        # update the tables
        self.updateTables()

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
            old_thickness, lock = self.data[snum]
            self.data[snum] = thickness, lock
        
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


