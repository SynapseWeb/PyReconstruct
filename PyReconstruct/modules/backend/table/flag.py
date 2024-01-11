from PySide6.QtCore import Qt

from PyReconstruct.modules.gui.table import FlagTableWidget
from PyReconstruct.modules.datatypes import (
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
        self.series_states = self.mainwindow.field.series_states
    
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
        self.mainwindow.field.refreshTables(refresh_data=True)
    
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
    
    def deleteFlags(self, flags : list, match_name=False):
        """Delete an object or objects on every section.
        
            Params:
                flags (list): the list of flags to delete
                match_name (bool): True if flags with same name should be deleted
        """
        self.mainwindow.saveAllData()

        # organize flags into dictionary
        flags_dict = {}
        for flag in flags:
            snum = flag.snum
            if snum not in flags_dict:
                flags_dict[snum] = []
            flags_dict[snum].append(flag)

        # iterate through sections and delete
        for snum, section in self.series.enumerateSections(
            message="Deleting flag(s)...",
            series_states=self.series_states
        ):
            if snum in flags_dict:
                for delete_flag in flags_dict[snum]:
                    for section_flag in section.flags.copy():
                        if match_name and section_flag.name == delete_flag.name:
                            section.removeFlag(section_flag)
                        elif not match_name and section_flag.equals(delete_flag):
                            section.removeFlag(section_flag)
                            break
                section.save()
                # update the tables
                self.updateSection(section)
        
        # update the view
        self.mainwindow.field.reload()
        self.mainwindow.seriesModified(True)

    def editFlag(self, old_flag : Flag, new_flag : Flag):
        """Edit a flag.
        
            Params:
                snum (int): the section number containing the flag
                flag (Flag): the flag to modify
                new_flag (Flag): the flag to replace
        """
        self.mainwindow.saveAllData()
        self.series_states.addState()

        section = self.series.loadSection(old_flag.snum)
        for i, flag in enumerate(section.flags):
            if old_flag.equals(flag):
                section.flags[i] = new_flag
                section.flags_modified = True
                break
        section.save()
        
        # manually create a section and series state
        self.series_states[section].addState(section, self.series)
        self.series_states.addSectionUndo(section.n)

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

        # organize flags into dictionary
        flags_dict = {}
        for flag in flags:
            snum = flag.snum
            if snum not in flags_dict:
                flags_dict[snum] = []
            flags_dict[snum].append(flag)

        # iterate through sections and resolve
        for snum, section in self.series.enumerateSections(
            message="Modifying flag(s)...",
            series_states=self.series_states
        ):
            if snum in flags_dict:
                for modify_flag in flags_dict[snum]:
                    for section_flag in section.flags:
                        if section_flag.equals(modify_flag):
                            section_flag.resolve(self.series.user, resolved)
                            section.flags_modified = True
                            break
                section.save()
                # update the tables
                self.updateSection(section)
        
        # update the view
        self.mainwindow.field.reload()
        self.mainwindow.seriesModified(True)

    def close(self):
        """Close all tables."""
        for table in self.tables:
            table.close()


