import re
import os

from PySide6.QtWidgets import (
    QMainWindow, 
    QDockWidget, 
    QTableWidgetItem,  
    QWidget, 
    QInputDialog, 
    QMenu, 
    QAbstractItemView,
    QColorDialog
)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt

from .copy_table_widget import CopyTableWidget

from PyReconstruct.modules.datatypes import Series, Section, Flag
from PyReconstruct.modules.gui.utils import (
    populateMenuBar,
    populateMenu,
    notify
)
from PyReconstruct.modules.gui.dialog import (
    FlagDialog,
    QuickDialog,
    FileDialog
)

class FlagTableWidget(QDockWidget):

    def __init__(self, series : Series, mainwindow : QWidget, manager):
        """Create the object table dock widget.
        
            Params:
                series (Series): the Series object
                mainwindow (MainWindow): the main window the dock is connected to
                manager: the object table manager
        """
        # initialize the widget
        super().__init__(mainwindow)
        self.series = series
        self.mainwindow = mainwindow

        # set desired format for widget
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)  # can be docked to right or left side
        self.setWindowTitle("Flag List")

        # set defaults
        self.columns = self.series.getOption("flag_columns")
        # check for missing
        defaults = self.series.getOption("flag_columns", get_default=True)
        for col_name in defaults:
            if col_name not in self.columns:
                self.columns = defaults
                self.series.setOption("flag_columns", self.columns)
                break

        self.show_resolved = False
        self.re_filters = set([".*"])
        self.color_filter = None
        self.comment_filter = None

        # create the main window widget
        self.main_widget = QMainWindow()
        self.setWidget(self.main_widget)
        
        # create the table and the menu
        self.table = None
        self.displayed_flags = []
        self.createTable()
        self.createMenus()

        # save manager object
        self.manager = manager

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
            ("deletematchname_act", "Delete flags with this name", "", lambda : self.deleteFlags(True))
        ]
        self.context_menu = QMenu(self)
        populateMenu(self, self.context_menu, context_menu_list)
    
    def setRow(self, flag : Flag, row : int, resize=True):
        """Set the data for a row of the table.
        
            Params:
                name (str): the name of the object
                row (int): the row to enter this data into
        """
        self.process_check_event = False
        col = 0
        if self.columns["Section"]:
            self.table.setItem(row, col, QTableWidgetItem(str(flag.snum)))
            col += 1
        if self.columns["Color"]:
            item = QTableWidgetItem(" ")
            item.setBackground(QColor(*flag.color))
            self.table.setItem(row, col, item)
            col += 1
        if self.columns["Flag"]:
            self.table.setItem(row, col, QTableWidgetItem(flag.name))
            col += 1
        if self.columns["Resolved"]:
            resolved = "Resolved" if flag.resolved else "Unresolved"
            self.table.setItem(row, col, QTableWidgetItem(resolved))
        if self.columns["Last Comment"]:
            if flag.comments:
                comment = flag.comments[-1].text
            else:
                comment = ""
            self.table.setItem(row, col, QTableWidgetItem(comment))
            col += 1
        
        self.displayed_flags[row] = flag
        
        if resize:
            self.table.resizeColumnsToContents()
            self.table.resizeRowToContents(row)
    
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
    
    def getFilteredFlags(self, section : Section = None):
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
    
    def createTable(self):
        """Create the table widget.
        
            Params:
                objdata (dict): the dictionary containing the object table data objects
        """
        # close an existing table and save scroll position
        if self.table is not None:
            vscroll = self.table.verticalScrollBar()
            scroll_pos = vscroll.value()
            self.table.close()
        else:
            scroll_pos = 0
        
        self.updateTitle()

        # establish table headers
        self.horizontal_headers = []
        for key, b in self.columns.items():
            if b:
                self.horizontal_headers.append(key)
        
        # filter the objects
        passing_flags = self.getFilteredFlags()

        # create the table object
        self.table = CopyTableWidget(len(passing_flags), len(self.horizontal_headers), self.main_widget)
        self.displayed_flags = [None] * len(passing_flags)

        # connect table functions
        self.table.mouseDoubleClickEvent = self.find
        self.table.contextMenuEvent = self.flagContextMenu
        self.table.backspace = self.deleteFlags

        # format table
        # self.table.setWordWrap(False)
        self.table.setShowGrid(False)  # no grid
        self.table.setAlternatingRowColors(True)  # alternate row colors
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # cannot be edited
        self.table.setHorizontalHeaderLabels(self.horizontal_headers)  # titles
        self.table.verticalHeader().hide()  # no veritcal header
        
        # fill in object data
        for r, flag in enumerate(passing_flags):
            self.setRow(flag, r, resize=False)

        # format rows and columns
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

        # set the saved scroll value
        self.table.verticalScrollBar().setValue(scroll_pos)

        # set table as central widget
        self.main_widget.setCentralWidget(self.table)
    
    def updateSection(self, section : Section):
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
    
    def resizeEvent(self, event):
        """Resize the table when window is resized."""
        super().resizeEvent(event)
        w = event.size().width()
        h = event.size().height()
        self.table.resize(w, h-20)
    
    def getSelectedFlag(self):
        """Get the name of the object highlighted by the user.
        
            Returns:
                (str): the name of the object
        """
        selected_indexes = self.table.selectedIndexes()
        if len(selected_indexes) != 1:
            return None
        return self.displayed_flags[selected_indexes[0].row()]
    
    def getSelectedFlags(self):
        """Get the name of the objects highlighted by the user.
        
            Returns:
                (list): the name of the objects
        """
        selected_indexes = self.table.selectedIndexes()
        return [self.displayed_flags[i.row()] for i in selected_indexes]

    # RIGHT CLICK FUNCTIONS

    def flagContextMenu(self, event=None):
        """Executed when button is right-clicked: pulls up menu for user to modify objects."""
        if len(self.table.selectedIndexes()) == 0:
            return
        self.context_menu.exec(event.globalPos())
    
    def editFlag(self):
        """Edit a flag."""
        flag = self.getSelectedFlag()
        if not flag:
            notify("Please edit one flag at a time.")
            return
        
        response, confirmed = FlagDialog(self.mainwindow, flag).exec()
        if not confirmed:
            return
        
        nf = flag.copy()
        nf.name, nf.color, nf.comments, new_comment, resolved = response
        if new_comment: nf.addComment(self.series.user, new_comment)
        nf.resolve(self.series.user, resolved)

        # keep track of scroll bar position
        vscroll = self.table.verticalScrollBar()
        scroll_pos = vscroll.value()

        self.manager.editFlag(flag, nf)
        
        # reset scroll bar position
        vscroll.setValue(scroll_pos)
    
    def markResolved(self, resolved=True):
        """Mark a flag as resolved or unresolved.
            
            Params:
                resolved (bool): the resolved status
        """
        flags = self.getSelectedFlags()
        if not flags:
            return
        
        self.manager.markResolved(flags, resolved)

    def deleteFlags(self, match_name=False):
        """Delete an object or objects on every section."""
        self.mainwindow.saveAllData()
        selected_flags = self.getSelectedFlags()
        self.manager.deleteFlags(selected_flags, match_name)

    # MENU-RELATED FUNCTIONS

    def refresh(self):
        """Refresh the object lists."""
        self.manager.refresh()
    
    def setColumns(self):
        """Set the columns to display."""
        structure = [
            [("check", *tuple(self.columns.items()))]
        ]
        response, confirmed = QuickDialog.get(self, structure, "Table Columns")
        if not confirmed:
            return
        self.columns = dict(response[0])
        self.series.setOption("flag_columns", self.columns)
        
        self.manager.updateTable(self)
    
    def export(self):
        """Export the object list as a csv file."""
        # get the location from the user
        file_path = FileDialog.get(
            "save",
            self,
            "Save Object List",
            file_name="objects.csv",
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
        # object data
        for r in range(self.table.rowCount()):
            items = []
            for c in range(self.table.columnCount()):
                items.append(self.table.item(r, c).text())
            csv_file.write(",".join(items) + "\n")
        # close file
        csv_file.close()
    
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
        self.manager.updateTable(self)
    
    def setColorFilter(self, use_selected=True):
        """Set the color filter for the list."""
        if use_selected:
            flag = self.getSelectedFlag()
            if not flag:
                notify("Please select one flag to set the color filter.")
                return
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
        self.manager.updateTable(self)
    
    def removeColorFilter(self):
        """Remove the color filter."""
        self.color_filter = None
        self.createTable()
    
    def find(self, event=None):
        """Focus the field on a flag in the series."""
        flag = self.getSelectedFlag()
        if flag is None:
            return
        self.mainwindow.setToFlag(flag)
    
    def closeEvent(self, event):
        """Remove self from manager table list."""
        self.manager.tables.remove(self)
        super().closeEvent(event)