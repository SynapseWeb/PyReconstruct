"""Application navigation operations."""

from PySide6.QtWidgets import QInputDialog

from PyReconstruct.modules.datatypes import Flag

class NavigationOperations:

    def changeSection(self, section_num : int = None, save=True):
        """Change the section of the field.
        
            Params:
                section_num (int): the section number to change to
                save (bool): saves data to files if True
        """
        if section_num is None:
            
            section_num, confirmed = QInputDialog.getText(
                self,
                "Go To Section",
                "Enter a section number:",
                text=str(self.series.current_section))
            if not confirmed:
                return
            try:
                section_num = int(section_num)
            except ValueError:
                return
        
        # end the field pending events
        self.field.endPendingEvents()
        # save data
        if save:
            self.saveAllData()
        # change the field section
        self.field.changeSection(section_num)
        # update status bar
        self.field.updateStatusBar()
        # update the mouse palette
        self.mouse_palette.updateBC()
    
    def incrementSection(self, down=False):
        """Increment the section number by one.
        
            Params:
                down (bool): the direction to move
        """
        section_numbers = sorted(list(self.series.sections.keys()))  # get list of section numbers
        section_number_i = section_numbers.index(self.series.current_section)  # get current section index
        if down:
            if section_number_i > 0:
                self.changeSection(section_numbers[section_number_i - 1])  
        else:   
            if section_number_i < len(section_numbers) - 1:
                self.changeSection(section_numbers[section_number_i + 1])       
    
    def setToObject(self, obj_name : str, section_num : int):
        """Focus the field on an object from a specified section.
        
            Params:
                obj_name (str): the name of the object
                section_num (int): the section the object is located
        """
        if obj_name is not None and section_num is not None:
            self.changeSection(section_num)
            self.field.findContour(obj_name)
            self.field.setFocus()
    
    def setToFlag(self, flag : Flag):
        """Focus the field on a flag.
        
            Params:
                flag (Flag): the flag
        """
        if flag is not None:
            self.changeSection(flag.snum)
            self.field.findFlag(flag)
            self.field.setFocus()
    
    def findObjectFirst(self, obj_name=None):
        """Find the first or last contour in the series.
        
            Params:
                obj_name (str): the name of the object to find
        """
        if obj_name is None:
            obj_name, confirmed = QInputDialog.getText(
                self,
                "Find Object",
                "Enter the object name:",
            )
            if not confirmed:
                return

        # find the contour
        self.setToObject(obj_name, self.series.data.getStart(obj_name))
    
