from PySide6.QtCore import Qt

from modules.gui.table import FlagTableWidget
from modules.datatypes import (
    Series,
    Section,
    Flag
)

class FlagTableManager():

    def __init__(self, series : Series, mainwindow):
        """Create the object table manager.
        
            Params:
                series (Series): the series object
                mainwindow (MainWindow): the parent main window object
        """
        self.tables = []
        self.series = series
        self.mainwindow = mainwindow
    
    def newTable(self):
        """Create a new object list widget."""
        new_table = FlagTableWidget(
            self.series,
            self.mainwindow,
            self
        )
        self.tables.append(new_table)
        self.mainwindow.addDockWidget(Qt.LeftDockWidgetArea, new_table)
    
    def updateSection(self, section : Section):
        """Update the data and the table for a specific section.
        
            Params:
                section (Section): the section object
                section_num (int): the section number
        """
        # refresh any removed traces
        for table in self.tables:
            table.updateSection(section)

    # MENU FUNCTIONS

    def refresh(self):
        """Reload all of the section data."""
        self.mainwindow.saveAllData()
        self.series.data.refresh()
        self.updateTables()
    
    def updateTable(self, table : FlagTableWidget):
        """Updates a table with the current data.
        
            Params:
                table (ObjectTableWidget): the table to update
        """
        table.createTable()
    
    def updateTables(self):
        """Update all tables."""
        for table in self.tables:
            table.createTable()
    
    def deleteFlags(self, flags : list):
        """Delete an object or objects on every section.
        
            Params:
                flags (list): the list of flags to delete
        """
        self.mainwindow.saveAllData()

        # organize flags into dictionary
        flags_dict = {}
        for snum, flag in flags:
            if snum not in flags_dict:
                flags_dict[snum] = []
            flags_dict[snum].append(flag)

        # iterate through sections and delete
        for snum, section in self.series.enumerateSections(message="Deleting flag(s)..."):
            if snum in flags_dict:
                for delete_flag in flags_dict[snum]:
                    for section_flag in section.flags:
                        if section_flag.equals(delete_flag):
                            section.flags.remove(section_flag)
                            break
                section.save()
                # update the tables
                self.updateSection(section)
        
        # update the view
        self.mainwindow.field.reload()
        self.mainwindow.seriesModified(True)

    def editFlag(self, snum : int, old_flag : Flag, new_flag : Flag):
        """Edit a flag.
        
            Params:
                snum (int): the section number containing the flag
                flag (Flag): the flag to modify
                new_flag (Flag): the flag to replace
        """
        self.mainwindow.saveAllData()

        section = self.series.loadSection(snum)
        for i, flag in enumerate(section.flags):
            if old_flag.equals(flag):
                section.flags[i] = new_flag
                break
        section.save()

        self.updateSection(section)

        # update the view
        self.mainwindow.field.reload()
        self.mainwindow.seriesModified(True)
    
    def markResolved(self, flags : list, resolved : bool):
        """Edit the resolved status of a flag.
        
            Params:
                flags (list): the list of flags to modify
                resolved (bool): the resolve status to set for the flag
        """
        self.mainwindow.saveAllData()

        for snum, flag in flags:
            section = self.series.loadSection(snum)
            for i, f in enumerate(section.flags):
                if flag.equals(f):
                    f.resolved = resolved
                    break
            section.save()

        self.updateSection(section)

        # update the view
        self.mainwindow.field.reload()
        self.mainwindow.seriesModified(True)
    
    def close(self):
        """Close all tables."""
        for table in self.tables:
            table.close()


