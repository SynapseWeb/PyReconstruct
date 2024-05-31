import re

from PySide6.QtWidgets import (
    QTableWidgetItem,  
    QWidget, 
    QInputDialog, 
    QMenu, 
    QColorDialog
)
from PySide6.QtGui import QColor

from .data_table import DataTable

from PyReconstruct.modules.datatypes import Series, Section, Flag
from PyReconstruct.modules.gui.utils import (
    populateMenuBar,
    populateMenu,
    notify
)
from PyReconstruct.modules.gui.dialog import (
    FlagDialog,
    QuickDialog,
)

class FlagTableWidget(DataTable):

    def __init__(self, series : Series, mainwindow : QWidget, manager):
        """Create the object table dock widget.
        
            Params:
                series (Series): the Series object
                mainwindow (MainWindow): the main window the dock is connected to
                manager: the object table manager
        """
        # create the filters
        self.show_resolved = False
        self.re_filters = set([".*"])
        self.color_filter = None
        self.comment_filter = None

        # initialize the widget
        self.displayed_flags = []
        super().__init__("flag", series, mainwindow, manager)
        self.createTable()

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
                ]
            },
            {
                "attr_name": "filtermenu",
                "text": "Filter",
                "opts":
                [
                    ("displayresolved_act", "Display resolved flags", "checkbox", self.toggleDisplayResolved),
                    ("refilter_act", "Regex filter...", "", self.setREFilter),
                    {
                        "attr_name": "colormenu",
                        "text": "Color filter",
                        "opts":
                        [
                            ("colorfilter_act", "Set filter...", "", lambda : self.setColorFilter(False)),
                            ("removecolor_act", "Remove filter...", "", self.removeColorFilter)
                        ]
                    },
                    ("commentfilter_act", "Comment text...", "", self.setCommentFilter)
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
            ("editattribtues_act", "View / Edit...", "", self.editFlag),
            ("flagcolorfilter_act", "Use as color filter", "", self.setColorFilter),
            None,
            {
                "attr_name": "resolvemenu",
                "text": "Resolve",
                "opts":
                [
                    ("resolve_act", "Mark as resolved", "", self.markResolved),
                    ("unresolved_act", "Mark as unresolved", "", lambda : self.markResolved(False))
                ]
            },
            None,
            ("copy_act", "Copy", "", self.table.copy),
            None,
            ("delete_act", "Delete", "", self.deleteFlags),
            ("deletematchname_act", "Delete all flags with this name", "", self.deleteFlagName)
        ]
        self.context_menu = QMenu(self)
        populateMenu(self, self.context_menu, context_menu_list)
    
    def getItems(self, flag : Flag, item_type : str):
        """Get the QTableWidgetItem(s) for an attribute of a flag.
        
            Params:
                flag (Flag): the flag to retrieve the data for
                item_type (str): the specific data to be retrieved
        """
        items = []
        if item_type == "Section":
            items.append(QTableWidgetItem(str(flag.snum)))
        elif item_type == "Color":
            item = QTableWidgetItem(" ")
            item.setBackground(QColor(*flag.color))
            items.append(item)
        elif item_type == "Flag":
            items.append(QTableWidgetItem(flag.name))
        elif item_type == "Resolved":
            resolved = "Resolved" if flag.resolved else "Unresolved"
            items.append(QTableWidgetItem(resolved))
        elif item_type == "Last Comment":
            if flag.comments:
                comment = flag.comments[-1].text
            else:
                comment = ""
            items.append(QTableWidgetItem(comment))
        return items
    
    def setRow(self, flag : Flag, row : int, resize=True):
        """Set the data for a row of the table.
        
            Params:
                name (str): the name of the object
                row (int): the row to enter this data into
        """
        super().setRow(flag, row, resize)

        while len(self.displayed_flags) <= row:
            self.displayed_flags.append(None)
        self.displayed_flags[row] = flag
    
    def insertRow(self, r : int):
        """Add a row to the table.
        
            Params:
                r (int): the row to add to the table
        """
        self.table.insertRow(r)
        self.displayed_flags.insert(r, None)
    
    def removeRow(self, r : int):
        """Remove a row from the table.
        
            Params:
                r (int): the row to remove
        """
        self.table.removeRow(r)
        self.displayed_flags.pop(r)
            
    def passesFilters(self, flag : Flag):
        """Check if an object passes the filters.
        
            Params:
                name (str): the name of the object
        """
        # check resolved
        if not self.show_resolved and flag.resolved:
            return False
        
        # check regex
        passes_filters = False if self.re_filters else True
        for re_filter in self.re_filters:
            if bool(re.fullmatch(re_filter, flag.name)):
                passes_filters = True
        if not passes_filters:
            return False
        
        # check color
        if self.color_filter and tuple(flag.color) != self.color_filter:
            return False
        
        # check comments
        if self.comment_filter:
            text_found = False
            for comment in flag.comments:
                if self.comment_filter in comment.text:
                    text_found = True
                    break
            if not text_found:
                return False
        
        return True
    
    def getFiltered(self, section : Section = None):
        """Get the flags that pass the filters."""
        passing_flags = []
        for snum, data in self.series.data["sections"].items():
            if section and section.n == snum:
                flags = section.flags
            else:
                flags = data["flags"]
            for flag in flags:
                if self.passesFilters(flag):
                    passing_flags.append(flag)
        return passing_flags
    
    def updateTitle(self):
        """Update the title of the table."""
        is_regex = tuple(self.re_filters) != (".*",)
        is_color = bool(self.color_filter)
        is_comment = bool(self.comment_filter)

        title = "Flag List "
        if any((is_regex, is_color, is_comment)):
            strs = []
            if is_regex: strs.append("regex")
            if is_color: strs.append("color")
            if is_comment: strs.append("comments")
            title += f"(Filtered by: {', '.join(strs)})"
        
        self.setWindowTitle(title)
    
    def updateData(self, section : Section):
        """Update the flags for a section.
        
            Params:
                section (Section): the section to update
        """
        row, exists_in_table = self.table.getRowIndex(str(section.n))
        while exists_in_table:
            self.removeRow(row)
            row, exists_in_table = self.table.getRowIndex(str(section.n))
        
        for flag in sorted(section.flags):
            if self.passesFilters(flag):
                self.insertRow(row)
                self.setRow(flag, row)
                row += 1
    
    def getSelected(self, single=False):
        """Get the name of the objects highlighted by the user.

            Params:
                single (bool): True if only accept single selection
            Returns:
                (str | list): the name of the object(s)
        """
        selected_indexes = self.table.selectedIndexes()
        selected_flags = [self.displayed_flags[i.row()] for i in selected_indexes]

        if single:
            if len(selected_flags) != 1:
                notify("Please select only one flag for this option.")
                return
            else:
                return selected_flags[0]
        else:
            return selected_flags

    # RIGHT CLICK FUNCTIONS
    
    def editFlag(self):
        """Edit a flag."""
        flag = self.getSelected(single=True)
        if not flag:
            return
        
        response, confirmed = FlagDialog(self.mainwindow, flag).exec()
        if not confirmed:
            return
        
        new_flag = flag.copy()
        new_flag.name, new_flag.color, new_flag.comments, new_comment, resolved = response
        if new_comment: new_flag.addComment(self.series.user, new_comment)
        new_flag.resolve(self.series.user, resolved)

        # keep track of scroll bar position
        vscroll = self.table.verticalScrollBar()
        scroll_pos = vscroll.value()

        # edit the flag
        self.mainwindow.saveAllData()
        self.series_states.addState()

        section = self.series.loadSection(flag.snum)
        for i, f in enumerate(section.flags):
            if flag.equals(f):
                section.flags[i] = new_flag
                section.flags_modified = True
                break
        section.save()
        
        # manually create a section and series state
        self.series_states[section].addState(section, self.series)
        self.series_states.addSectionUndo(section.n)

        self.manager.updateFlags(section)

        # update the view
        self.mainwindow.field.reload()
        self.mainwindow.seriesModified(True)
        
        # reset scroll bar position
        vscroll.setValue(scroll_pos)
    
    def markResolved(self, resolved=True):
        """Mark a flag as resolved or unresolved.
            
            Params:
                resolved (bool): the resolved status
        """
        flags = self.getSelected()
        if not flags:
            return
        
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
                self.manager.updateFlags(section)
        
        # update the view
        self.mainwindow.field.reload()
        self.mainwindow.seriesModified(True)

    def deleteFlags(self):
        """Delete a flag or flags."""
        self.mainwindow.saveAllData()
        flags = self.getSelected()

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
                        if section_flag.equals(delete_flag):
                            section.removeFlag(section_flag)
                            break
                section.save()
                # update the tables
                self.manager.updateFlags(section)
        
        # update the view
        self.mainwindow.field.reload()
        self.mainwindow.seriesModified(True)
    
    def deleteFlagName(self):
        """Delete all flags with a certain name."""
        self.mainwindow.saveAllData()
        flags = self.getSelected()
        if not flags:
            return
        names = set(f.name for f in flags)

        # iterate through sections and delete
        for snum, section in self.series.enumerateSections(
            message="Deleting flag(s)...",
            series_states=self.series_states
        ):
            for section_flag in section.flags.copy():
                if section_flag.name in names:
                    section.removeFlag(section_flag)
                section.save()
                # update the tables
                self.manager.updateFlags(section)
        
        # update the view
        self.mainwindow.field.reload()
        self.mainwindow.seriesModified(True)

    
    def backspace(self):
        """Called when backspace is pressed."""
        self.deleteFlags()

    # MENU-RELATED FUNCTIONS
    
    def toggleDisplayResolved(self):
        """Toggle whether or not resolved flags are displayed in the table."""
        self.show_resolved = self.displayresolved_act.isChecked()
        self.createTable()
    
    def setREFilter(self):
        """Set a new regex filter for the list."""
        # get a new filter from the user
        structure = [
            ["Enter the regex filter(s) below"],
            [("multitext", self.re_filters)]
        ]
        response, confirmed = QuickDialog.get(self, structure, "Regex Filters")
        if not confirmed:
            return
        
        self.re_filters = set(response[0] if response[0] else [".*"])
        self.re_filters = set([s.replace("#", "[0-9]") for s in self.re_filters])

        # call through manager to update self
        self.manager.recreateTable(self)
    
    def setColorFilter(self, use_selected=True):
        """Set the color filter for the list."""
        if use_selected:
            flags = self.getSelected()
            if not flags:
                return
            elif len(flags) != 1:
                notify("Please select one flag to set the color filter.")
                return
            flag = flags[0]
            self.color_filter = tuple(flag.color)
        else:
            if self.color_filter:
                c = QColorDialog.getColor(
                    QColor(*self.color_filter)
                )
            else:
                c = QColorDialog.getColor()
            if not c:
                return
            self.color_filter = (c.red(), c.green(), c.blue())

        self.createTable()
    
    def setCommentFilter(self):
        """Set a new regex filter for the comments."""
        # get a new filter from the user
        new_filter, confirmed = QInputDialog.getText(
            self,
            "Filter Comments",
            "Enter the text to find in the flag comments:",
            text=self.comment_filter
        )
        if not confirmed:
            return
        
        self.comment_filter = new_filter

        # call through manager to update self
        self.manager.recreateTable(self)
    
    def removeColorFilter(self):
        """Remove the color filter."""
        self.color_filter = None
        self.createTable()
    
    def mouseDoubleClickEvent(self, event=None):
        """Focus the field on a flag in the series."""
        super().mouseDoubleClickEvent(event)
        flag = self.getSelected(single=True)
        if flag is None:
            return
        self.mainwindow.setToFlag(flag)