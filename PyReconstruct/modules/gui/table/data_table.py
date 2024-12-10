from PySide6.QtWidgets import (
    QMainWindow, 
    QDockWidget, 
    QTableWidgetItem,  
    QWidget, 
    QAbstractItemView,
    QMenu,
)
from PySide6.QtCore import Qt

from .copy_table_widget import CopyTableWidget

from PyReconstruct.modules.datatypes import Series
from PyReconstruct.modules.gui.dialog import (
    FileDialog,
    TableColumnsDialog
)

class DataTable(QDockWidget):

    def __init__(self, data_name : str, series : Series, mainwindow : QWidget, manager):
        """Create the object table dock widget.
        
            Params:
                data_name (str): the name of the type of data being displayed (object, trace, ztrace, section, or flag)
                series (Series): the Series object
                mainwindow (MainWindow): the main window the dock is connected to
                manager: the object table manager
        """
        # initialize the widget
        super().__init__(mainwindow)
        self.name = data_name
        self.series = series
        self.mainwindow = mainwindow

        # get the series states
        self.series_states = manager.series_states

        # set desired format for widget
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)  # can be docked to right or left side
        self.setWindowTitle(f"{self.name.capitalize()} List")

        # set defaults
        if "static_columns" not in dir(self): self.static_columns = []
        self.columns = self.series.getOption(f"{self.name}_columns")
        # check for missing default columns
        defaults = self.series.getOption(f"{self.name}_columns", get_default=True)
        for col_name, b in defaults:
            if col_name not in dict(self.columns):
                self.columns.append((col_name, b))
                self.series.setOption(f"{self.name}_columns", self.columns)
        self.table = None
        self.process_check_event = False
        self.horizontal_headers = self.getHeaders()

        # create the main window widget
        self.main_widget = QMainWindow()
        self.setWidget(self.main_widget)

        # save manager object
        self.manager = manager
    
    def createMenus(self):
        """Create the menubar and context menu for the widget.
        
        This must be overwritten in child classes.
        """
        self.menubar = self.main_widget.menuBar()
        self.context_menu = QMenu(self)
    
    def getHeaders(self):
        """Get the column headers for the table.
        
        This should be overwritten in child classes.
        """
        return self.static_columns + [k for k, v in self.columns if v]
    
    def getItems(self, container, item_type : str):
        """Get the QTableWidgetItem(s) for a data attribute.

        This must be overwritten in child classes.
        
            Params:
                container: the Python object that provides the necessary data
                item_type (str): the specific data to be retrieved
        """
        return QTableWidgetItem("")
    
    def setRow(self, container, row : int, resize=True):
        """Set the data for a row of the table.
        
            Params:
                container: the Python object that provides the necessary data
                row (int): the row to enter this data into
        """
        self.process_check_event = False
        col = 0

        for key in self.static_columns:
            items = self.getItems(container, key)
            for item in items:
                self.table.setItem(row, col, item)
                col += 1
        for key, b in self.columns:
            if b:
                items = self.getItems(container, key)
                for item in items:
                    self.table.setItem(row, col, item)
                    col += 1
        
        if resize:
            self.table.resizeColumnsToContents()
            self.table.resizeRowToContents(row)

        self.process_check_event = True
    
    def passesFilters(self, container):
        """Check if data passes the filters.

        This should be overwritten in child classes.
        
            Params:
                container: the Python object that provides the necessary data
        """
        return True

    def getFiltered(self, data_list : list = []):
        """Get the data that pass the filters.
        
        This might be overwritten in child classes.

        Params:
            data_list (list): the list of data to filter
        """
        filtered_list = []
        for item in data_list:
            if self.passesFilters(item):
                filtered_list.append(item)
        
        return filtered_list

    def updateData(self):
        """Update the data for the table.
        
        This must be overwritten in child classes.
        """

    def createTable(self):
        """Create the table widget.
        
        This function is primarily involved in creating the GUI. It does not handle a significant amount of logic.
        """
        # close an existing table and save scroll position
        if self.table is not None:
            vscroll = self.table.verticalScrollBar()
            scroll_pos = vscroll.value()
            self.table.close()
        else:
            scroll_pos = 0

        # update the columns
        self.columns = self.series.getOption(f"{self.name}_columns")

        # establish table headers
        self.horizontal_headers = self.getHeaders()
        
        # filter the data
        filtered_data = self.getFiltered()

        # create the table object
        self.table = CopyTableWidget(self, len(filtered_data), len(self.horizontal_headers), self.main_widget)

        # connect table functions
        self.table.mouseDoubleClickEvent = self.mouseDoubleClickEvent
        self.table.backspace = self.backspace
        self.table.itemChanged.connect(self.itemChanged)

        # format table
        # self.table.setWordWrap(False)
        self.table.setShowGrid(False)  # no grid
        self.table.setAlternatingRowColors(True)  # alternate row colors
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # cannot be edited
        self.table.setHorizontalHeaderLabels(self.horizontal_headers)  # titles
        self.table.verticalHeader().hide()  # no veritcal header
        
        # fill in object data
        for r, n in enumerate(filtered_data):
            self.setRow(n, r, resize=False)

        # format rows and columns
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

        # set the saved scroll value
        self.table.verticalScrollBar().setValue(scroll_pos)

        # set table as central widget
        self.main_widget.setCentralWidget(self.table)

        # set the title
        self.updateTitle()

        # update the menus
        self.createMenus()
    
    def updateTitle(self):
        """Update the title of the widget."""
        self.setWindowTitle(f"{self.name.capitalize()} List")
        
    def resizeEvent(self, event):
        """Resize the table when window is resized."""
        super().resizeEvent(event)
        w = event.size().width()
        h = event.size().height()
        self.table.resize(w, h-20)

    def getSelected(self, single=False):
        """Get the selected data item(s).
        
        Must be overwritten in child classes.

            Params:
                single (bool): True if only accept single selection
        """
        pass
    
    def contextMenuEvent(self, event=None):
        """Executed when button is right-clicked: pulls up menu for user."""
        super().contextMenuEvent(event)

        self.mainwindow.field.focus_table_id = self.table.id

        items = self.getSelected()
        if not items:
            return

        self.context_menu.exec(event.globalPos())   

    def itemChanged(self, item : QTableWidgetItem):
        """User checked a checkbox.

        Should be overwritten in future classes
        
            Params:
                item (QTableWidgetItem): the item that was checked
        """
        pass

    def refresh(self):
        """Refresh the object lists."""
        self.manager.refresh()
    
    def setColumns(self):
        """Set the columns to display."""
        response, confirmed = TableColumnsDialog(self, self.columns).exec()

        if not confirmed:
            return

        self.columns = response
        self.series.setOption(f"{self.name}_columns", self.columns.copy())
        
        self.manager.recreateTable(self)
    
    def export(self):
        """Export datatable as a csv file."""

        ## Query user for location
        file_path = FileDialog.get(
            "save",
            self,
            "Save List",
            file_name=f"{self.name}.csv",
            filter="Comma Separated Values (*.csv)"
        )
        if not file_path:
            return
        
        csv_file = open(file_path, "w")
        
        ## Headers first
        items = []
        checkable = []
        
        for c in range(self.table.columnCount()):
            
            header_item = self.table.horizontalHeaderItem(c)
            header_title = header_item.text()

            ## Track checkable item cols
            if header_title in ("Hidden", "Closed"):
                checkable.append(c)
            
            items.append(header_title)
            
        csv_file.write(",".join(items) + "\n")
        
        ## Then data
        for r in range(self.table.rowCount()):
            
            items = []
            
            for c in range(self.table.columnCount()):

                cell = self.table.item(r, c)
                
                if c in checkable:  # hidden and closed cols

                    if cell.checkState() == Qt.Checked:

                        cell_text = "yes"

                    else:

                        cell_text = "no"

                else:

                    cell_text = cell.text()

                    if "," in cell_text:  # e.g., multiple tags
                        
                        cell_text = cell_text.replace(",", "")
                    
                items.append(cell_text)
                
            csv_file.write(",".join(items) + "\n")

        csv_file.close()
    
    def backspace(self):
        """Called when user hits delete or backspace.
        
        Should be overwritten in child classes.
        """
        pass

    def copy(self):
        """Copy text from the table"""
        return self.table.copy()
    
    def closeEvent(self, event):
        """Remove self from manager table list."""
        self.manager.tables[self.name].remove(self)
        super().closeEvent(event)

