import re
import os
from datetime import datetime

from PySide6.QtWidgets import (
    QMainWindow, 
    QDockWidget, 
    QTableWidgetItem,  
    QWidget, 
    QInputDialog, 
    QMenu, 
    QAbstractItemView,
    QApplication,
    QMessageBox
)
from PySide6.QtCore import Qt

from .copy_table_widget import CopyTableWidget
from .history import HistoryTableWidget
from .str_helper import sortList

from PyReconstruct.modules.datatypes import Series
from PyReconstruct.modules.gui.utils import (
    populateMenuBar,
    populateMenu,
    notify,
    notifyLocked
)
from PyReconstruct.modules.gui.dialog import (
    ObjectGroupDialog,
    TraceDialog,
    ShapesDialog,
    QuickDialog,
    FileDialog
)

class ObjectTableWidget(QDockWidget):

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
        self.series_states = self.mainwindow.field.series_states

        # set desired format for widget
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)  # can be docked to right or left side
        self.setWindowTitle("Object List")

        # set defaults
        self.columns = self.series.getOption("object_columns")
        # check for missing columns
        defaults = self.series.getOption("object_columns", get_default=True)
        for col_name in defaults:
            if col_name not in self.columns:
                self.columns = defaults
                self.series.setOption("object_columns", self.columns)
                break
        
        self.re_filters = set([".*"])
        self.tag_filters = set()
        self.group_filters = set()
        self.cr_status_filter = {
            "Blank": True,
            "Needs curation": True,
            "Curated": True
        }
        self.cr_user_filters = set()

        # create the main window widget
        self.main_widget = QMainWindow()
        self.setWidget(self.main_widget)
        
        # create the table and the menu
        self.table = None
        self.process_check_event = False
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
                    ("refilter_act", "Regex filter...", "", self.setREFilter),
                    ("groupfilter_act", "Group filter...", "", self.setGroupFilter),
                    ("tagfilter_act", "Tag filter...", "", self.setTagFilter),
                    ("crstatusfilter_act", "Curation filter...", "", self.setCRFilter)
                ]
            },
            {
                "attr_name": "findmenu",
                "text": "Find",
                "opts":
                [
                    ("findfirst_act", "First", "", self.findFirst),
                    ("findlast_act", "Last", "", self.findLast)
                ]
            },

            {
                "attr_name": "groupmenu",
                "text": "Groups",
                "opts":
                [
                    ("renamegroup_act", "Rename group...", "", self.renameGroup),
                    ("deletegroup_act", "Delete group...", "", self.deleteGroup)
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
            ("editattribtues_act", "Edit attributes of traces...", "", self.editAttributes),
            None,
            {
                "attr_name" : "objattrsmenu",
                "text": "Object attributes",
                "opts":
                [
                    ("editcomment_act", "Comment...", "", self.editComment),
                    None,
                    ("addgroup_act", "Add to group...", "", self.addToGroup),
                    ("removegroup_act", "Remove from group...", "", self.removeFromGroup),
                    ("removeallgroups_act", "Remove from all groups", "", self.removeFromAllGroups),
                    None,
                    ("setalignment_act", "Change object alignment...", "", self.editAlignment),
                    None,
                    ("lockobj_act", "Lock", "", self.lockObjects),
                    ("unlockobj_act", "Unlock", "", lambda : self.lockObjects(False))
                ]
            },
            {
                "attr_name": "operationsmenu",
                "text": "Operations",
                "opts":
                [
                    ("editradius_act", "Edit radius...", "", self.editRadius),
                    ("editshape_act", "Edit shape...", "", self.editShape),
                    None,
                    ("splitobj_act", "Split traces into individual objects", "", self.splitObject),
                    None,
                    ("hideobj_act", "Hide", "", self.hideObj),
                    ("unhideobj_act", "Unhide", "", lambda : self.hideObj(False)),
                    None,
                    ("removealltags_act", "Remove all tags", "", self.removeAllTags),
                    None,
                    ("lockobj_act1", "Lock", "", self.lockObjects),
                    ("unlockobj_act1", "Unlock", "", lambda : self.lockObjects(False))
                ]
            },
            {
                "attr_name": "curatemenu",
                "text": "Set curation",
                "opts":
                [
                    ("blankcurate_act", "Blank", "", lambda : self.bulkCurate("")),
                    ("needscuration_act", "Needs curation", "", lambda : self.bulkCurate("Needs curation")),
                    ("curated_act", "Curated", "", lambda : self.bulkCurate("Curated"))
                ]
            },
            {
                "attr_name": "menu_3D",
                "text": "3D",
                "opts":
                [
                    ("addto3D_act", "Add to scene", "", self.addTo3D),
                    ("remove3D_act", "Remove from scene", "", self.remove3D),
                    {
                        "attr_name": "Export",
                        "text": "Export",
                        "opts":
                        [
                            ("export3D_act", "Wavefront (.obj)", "", lambda : self.exportAs3D("obj")),
                            ("export3D_act", "Object File Format (.off)", "", lambda : self.exportAs3D("off")),
                            ("export3D_act", "Stanford PLY (.ply)", "", lambda : self.exportAs3D("ply")),
                            ("export3D_act", "Stl (.stl)", "", lambda : self.exportAs3D("stl")),
                            ("export3D_act", "Collada (.dae) - requires collada", "", lambda : self.exportAs3D("dae")),
                        ]
                        
                    },
                    None,
                    ("edit3D_act", "Edit 3D settings...", "", self.edit3D)
                ]
            },
            {
                "attr_name": "ztrace_menu",
                "text": "Create ztrace",
                "opts":
                [
                    ("csztrace_act", "On contour midpoints", "", self.createZtrace),
                    ("atztrace_act", "From trace sequence", "", lambda : self.createZtrace(cross_sectioned=False)),
                ]
            },
            None,
            ("history_act", "View history", "", self.viewHistory),
            None,
            ("setpalette_act", "Copy attributes to palette", "", self.setPalette),
            ("copy_act", "Copy", "", self.table.copy),
            None,
            ("delete_act", "Delete", "", self.deleteObjects)
        ]
        self.context_menu = QMenu(self)
        populateMenu(self, self.context_menu, context_menu_list)

        self.locked_actions = [
            "editattribtues_act",
            "editcomment_act",
            "addgroup_act",
            "removegroup_act",
            "removeallgroups_act",
            "setalignment_act",
            "editradius_act",
            "editshape_act",
            "splitobj_act",
            "hideobj_act",
            "unhideobj_act",
            "removealltags_act",
            "curatemenu",
            "delete_act",
        ]
    
    def updateTitle(self):
        """Update the title of the table."""
        is_regex = tuple(self.re_filters) != (".*",)
        is_tag = bool(self.tag_filters)
        is_group = bool(self.group_filters)
        is_cr = self.columns["Curate"] and (
            bool(self.cr_user_filters) or not all(self.cr_status_filter.values())
        )

        title = "Object List "
        if any((is_regex, is_tag, is_group, is_cr)):
            strs = []
            if is_regex: strs.append("regex")
            if is_tag: strs.append("tags")
            if is_group: strs.append("groups")
            if is_cr: strs.append("curation")
            title += f"(Filtered by: {', '.join(strs)})"
        
        self.setWindowTitle(title)
    
    def setRow(self, name : str, row : int, resize=True):
        """Set the data for a row of the table.
        
            Params:
                name (str): the name of the object
                row (int): the row to enter this data into
        """
        self.process_check_event = False
        self.table.setItem(row, 0, QTableWidgetItem(name))
        col = 1
        if self.columns["Range"]:
            self.table.setItem(row, col, QTableWidgetItem(str(self.series.data.getStart(name))))
            col += 1
            self.table.setItem(row, col, QTableWidgetItem(str(self.series.data.getEnd(name))))
            col += 1
        if self.columns["Count"]:
            self.table.setItem(row, col, QTableWidgetItem(str(self.series.data.getCount(name))))
            col += 1
        if self.columns["Flat area"]:
            self.table.setItem(row, col, QTableWidgetItem(str(round(self.series.data.getFlatArea(name), 5))))
            col += 1
        if self.columns["Volume"]:
            self.table.setItem(row, col, QTableWidgetItem(str(round(self.series.data.getVolume(name), 5))))
            col += 1
        if self.columns["Radius"]:
            self.table.setItem(row, col, QTableWidgetItem(str(round(self.series.data.getAvgRadius(name), 5))))
            col += 1
        if self.columns["Groups"]:
            groups = self.series.object_groups.getObjectGroups(name)
            groups_str = ", ".join(groups)
            self.table.setItem(row, col, QTableWidgetItem(groups_str))
            col += 1
        if self.columns["Trace tags"]:
            tags = self.series.data.getTags(name)
            tags_str = ", ".join(tags)
            self.table.setItem(row, col, QTableWidgetItem(tags_str))
            col += 1
        if self.columns["Locked"]:
            item = QTableWidgetItem("")
            item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            item.setCheckState(Qt.CheckState.Checked if self.series.getAttr(name, "locked") else Qt.CheckState.Unchecked)
            self.table.setItem(row, col, item)
            col += 1
        if self.columns["Last user"]:
            last_user = self.series.getAttr(name, "last_user")
            self.table.setItem(row, col, QTableWidgetItem(last_user))
            col += 1
        if self.columns["Curate"]:
            check_item = QTableWidgetItem("")
            status_item = QTableWidgetItem("")
            user_item = QTableWidgetItem("")
            date_item = QTableWidgetItem("")
            cr_items = [check_item, status_item, user_item, date_item]
            check_item.setFlags(Qt.ItemFlag.ItemIsUserTristate | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)

            obj_curation = self.series.getAttr(name, "curation")
            if not obj_curation:
                check_item.setCheckState(Qt.CheckState.Unchecked)
                cr_color = None
            else:
                curated, user, date = obj_curation
                if curated:
                    check_item.setCheckState(Qt.CheckState.Checked)
                    status_item.setText("Curated")
                    cr_color = Qt.cyan
                else:
                    check_item.setCheckState(Qt.CheckState.PartiallyChecked)
                    status_item.setText(f"Needs curation")
                    cr_color = Qt.yellow
                user_item.setText(user)
                date_item.setText(date)
            
            for item in cr_items:
                if cr_color:
                    item.setBackground(cr_color)
                self.table.setItem(row, col, item)
                col += 1
        if self.columns["Alignment"]:
            alignment = self.series.getAttr(name, "alignment")
            if alignment is None: alignment = ""
            self.table.setItem(row, col, QTableWidgetItem(alignment))
            col += 1
        if self.columns["Comment"]:
            comment = self.series.getAttr(name, "comment")
            self.table.setItem(row, col, QTableWidgetItem(comment))
            col += 1
        if resize:
            self.table.resizeColumnsToContents()
            self.table.resizeRowToContents(row)
        self.process_check_event = True
    
    def passesFilters(self, name : str):
        """Check if an object passes the filters.
        
            Params:
                name (str): the name of the object
        """
        # check groups
        filters_len = len(self.group_filters)
        if filters_len != 0:
            object_groups = self.series.object_groups.getObjectGroups(name)
            groups_len = len(object_groups)
            union_len = len(object_groups.union(self.group_filters))
            if union_len == groups_len + filters_len:  # intersection does not exist
                return False
        
        # check tags
        filters_len = len(self.tag_filters)
        if filters_len != 0:
            object_tags = self.series.data.getTags(name)
            object_len = len(object_tags)
            union_len = len(object_tags.union(self.tag_filters))
            if union_len == object_len + filters_len:  # intersection does not exist
                return False
        
        # check curation status and user
        if self.columns["Curate"]:
            obj_curation = self.series.getAttr(name, "curation")
            if obj_curation:
                cr_status, user, date = tuple(obj_curation)
                cr_status = "Curated" if cr_status else "Needs curation"
                if not self.cr_status_filter[cr_status]:
                    return False
                if self.cr_user_filters and user not in self.cr_user_filters:
                    return False          
            else:
                if not self.cr_status_filter["Blank"]:
                    return False
                if self.cr_user_filters:
                    return False
        
        # check regex
        passes_filters = False if self.re_filters else True
        for re_filter in self.re_filters:
            if bool(re.fullmatch(re_filter, name)):
                passes_filters = True
        if not passes_filters:
            return False
        
        return True

    def getFilteredObjects(self):
        """Get the names of the objects that pass the filter."""
        filtered_object_list = []
        for name in self.series.data["objects"]:
            if self.passesFilters(name):
                filtered_object_list.append(name)
        
        return sortList(filtered_object_list)

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

        # create the table title
        self.updateTitle()

        # establish table headers
        self.curate_column = None
        self.horizontal_headers = ["Name"]
        for key, b in self.columns.items():
            if b and key == "Range":
                self.horizontal_headers.append("Start")
                self.horizontal_headers.append("End")
            elif b and key == "Curate":
                self.curate_column = len(self.horizontal_headers)
                self.horizontal_headers.append("CR")
                self.horizontal_headers.append("Status")
                self.horizontal_headers.append("User")
                self.horizontal_headers.append("Date")
            elif b:
                self.horizontal_headers.append(key)
        
        # filter the objects
        filtered_obj_names = self.getFilteredObjects()

        # create the table object
        self.table = CopyTableWidget(len(filtered_obj_names), len(self.horizontal_headers), self.main_widget)

        # connect table functions
        self.table.mouseDoubleClickEvent = self.mouseDoubleClickEvent
        self.table.contextMenuEvent = self.objectContextMenu
        self.table.backspace = self.deleteObjects
        self.table.itemChanged.connect(self.itemChecked)

        # format table
        # self.table.setWordWrap(False)
        self.table.setShowGrid(False)  # no grid
        self.table.setAlternatingRowColors(True)  # alternate row colors
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # cannot be edited
        self.table.setHorizontalHeaderLabels(self.horizontal_headers)  # titles
        self.table.verticalHeader().hide()  # no veritcal header
        
        # fill in object data
        for r, n in enumerate(filtered_obj_names):
            self.setRow(n, r, resize=False)

        # format rows and columns
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()

        # set the saved scroll value
        self.table.verticalScrollBar().setValue(scroll_pos)

        # set table as central widget
        self.main_widget.setCentralWidget(self.table)
    
    def updateObjects(self, names):
        """Update the data for a set of objects.
        
            Params:
                names (iterable): the names of the objects to update
        """
        for name in names:
            # check if object passes filters
            if not self.passesFilters(name):
                # special case: does not pass filter anymore but exists on table
                row, exists_in_table = self.table.getRowIndex(name)
                if exists_in_table:
                    self.table.removeRow(row)
                return

            # update if it does
            row, exists_in_table = self.table.getRowIndex(name)
            if exists_in_table and name not in self.series.data["objects"]:  # completely delete object
                self.table.removeRow(row)
            elif exists_in_table and name in self.series.data["objects"]:  # update existing object
                self.setRow(name, row)
            elif not exists_in_table and name in self.series.data["objects"]:  # add new object
                self.table.insertRow(row)
                self.setRow(name, row)
        
        self.mainwindow.checkActions()
    
    def resizeEvent(self, event):
        """Resize the table when window is resized."""
        super().resizeEvent(event)
        w = event.size().width()
        h = event.size().height()
        self.table.resize(w, h-20)
    
    def mouseDoubleClickEvent(self, event):
        """Called when user double-clicks."""
        super().mouseDoubleClickEvent(event)

        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ShiftModifier:
            self.addTo3D()
        else:
            self.findFirst()
    
    def checkLocked(self, obj_names : list, lock_actions=True):
        """Check for locked objects within a list of obj names.
        
            Params:
                obj_list (list): the names to check
                lock_actions (bool): True if actions should be locked if locked object detected
        """
        locked = False
        for name in obj_names:
            if self.series.getAttr(name, "locked"):
                locked = True
                break
        
        if lock_actions:
            for act_name in self.locked_actions:
                getattr(self, act_name).setEnabled(not locked)
        
        return locked
    
    def getSelectedObject(self) -> str:
        """Get the name of the object highlighted by the user.
        
            Returns:
                (str): the name of the object
        """
        selected_indexes = self.table.selectedIndexes()
        if len(selected_indexes) != 1:
            return None
        r = selected_indexes[0].row()
        obj_name = self.table.item(r, 0).text()
        self.checkLocked([obj_name])
        return obj_name
    
    def getSelectedObjects(self) -> list[str]:
        """Get the name of the objects highlighted by the user.
        
            Returns:
                (list): the name of the objects
        """
        selected_indexes = self.table.selectedIndexes()
        obj_names = []
        for i in selected_indexes:
            r = i.row()
            n = self.table.item(r, 0).text()
            obj_names.append(n)
        
        self.checkLocked(obj_names)
        return obj_names

    def itemChecked(self, item : QTableWidgetItem):
        """User checked a curate checkbox."""
        # check for curation
        if not self.process_check_event:
            return
        
        self.process_check_event = False

        r = item.row()
        c = item.column()
        name = self.table.item(r, 0).text()
        state = item.checkState()

        # if locked box checked
        if self.horizontal_headers[c] == "Locked":
            self.series_states.addState()
            locked = state == Qt.CheckState.Checked
            self.series.setAttr(name, "locked", locked)
            self.setRow(name, r)
            if locked:
                self.mainwindow.field.deselectAllTraces()
            self.mainwindow.seriesModified(True)
        
        # curation box checked
        elif self.horizontal_headers[c] == "CR":
            if self.series.getAttr(name, "locked"):
                notify("This object is locked.")
                self.setRow(name, r)
                self.manager.updateObjects([name])
            else:
                self.series_states.addState()
                if state == Qt.CheckState.Unchecked:
                    self.series.setCuration([name], "")
                elif state == Qt.CheckState.PartiallyChecked:
                    assign_to, confirmed = QInputDialog.getText(
                        self,
                        "Assign to",
                        "Assign curation to username:\n(press enter to leave blank)" 
                    )
                    if not confirmed:
                        item.setCheckState(Qt.CheckState.Unchecked)
                        self.process_check_event = True
                        return
                    self.series.setCuration([name], "Needs curation", assign_to)
                elif state == Qt.CheckState.Checked:
                    self.series.setCuration([name], "Curated")

                self.setRow(name, r)
                self.manager.updateObjects([name])
                self.mainwindow.seriesModified(True)
        
        self.process_check_event = True

    # RIGHT CLICK FUNCTIONS

    def objectContextMenu(self, event=None):
        """Executed when button is right-clicked: pulls up menu for user to modify objects."""
        names = self.getSelectedObjects()  # also updates the available actions
        if not names:
            return

        self.context_menu.exec(event.globalPos())   
    
    def editAttributes(self):
        """Edit the name of an object in the entire series."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return

        # ask the user for the new object name
        if len(obj_names) == 1:
            displayed_name = obj_names[0]
            tags = self.series.data.getTags(obj_names[0])
        else:
            displayed_name = None
            tags=None
        
        response, confirmed = TraceDialog(
            self, 
            name=displayed_name, 
            tags=tags, 
            is_obj_list=True
        ).exec()

        if not confirmed:
            return
        
        attr_trace, sections = response
        
        # keep track of scroll bar position
        vscroll = self.table.verticalScrollBar()
        scroll_pos = vscroll.value()

        self.manager.editAttributes(obj_names, attr_trace, sections)
        
        # reset scroll bar position
        vscroll.setValue(scroll_pos)
    
    def editComment(self):
        """Edit the comment of the object."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return
        
        if len(obj_names) == 1:
            comment = self.series.getAttr(obj_names[0], "comment")
        else:
            comment = ""
        new_comment, confirmed = QInputDialog.getText(
            self,
            "Object Comment",
            "Comment:",
            text=comment
        )
        if not confirmed:
            return
        
        self.series_states.addState()
        
        for obj_name in obj_names:
            self.series.setAttr(obj_name, "comment", new_comment)
            self.series.addLog(obj_name, None, "Edit object comment")
        self.updateObjects(obj_names)

        self.mainwindow.seriesModified(True)
    
    def editAlignment(self):
        """Edit alignment for object(s)."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            notify("Please select one object to edit.")
            return
        
        structure = [
            ["Alignment:", ("combo", ["no-alignment"] + list(self.mainwindow.field.section.tforms.keys()))]
        ]
        response, confirmed = QuickDialog.get(self, structure, "Object Alignment")
        if not confirmed:
            return
        
        self.series_states.addState()
        
        alignment = response[0]
        if not alignment: alignment = None
        for obj_name in obj_names:
            self.series.setAttr(obj_name, "alignment", alignment)
            self.series.addLog(obj_name, None, "Edit default alignment")
        
        self.refresh()
        self.mainwindow.seriesModified(True)
        
    def editRadius(self):
        """Modify the radius of the trace on an entire object."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return
        
        new_rad, confirmed = QInputDialog.getText(
            self, 
            "Object Trace Radius",
            "Enter the new radius:",
        )
        if not confirmed:
            return

        try:
            new_rad = float(new_rad)
        except ValueError:
            return
        
        if new_rad <= 0:
            return
        
        for name in obj_names:
            a = self.series.getAttr(name, "alignment")
            if a and a != self.series.alignment:
                response = QMessageBox.question(
                    self,
                    "Alignment Conflict",
                    "The field alignment does not match the object alignment.\nWould you like to continue?",
                    buttons=(
                        QMessageBox.Yes |
                        QMessageBox.No 
                    )
                )
                if response != QMessageBox.Yes:
                    return
        
        self.manager.editRadius(obj_names, new_rad)
    
    def editShape(self):
        """Modify the shape of the traces on an entire object."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return
        
        new_shape, confirmed = ShapesDialog(self).exec()
        if not confirmed:
            return
        
        self.manager.editShape(obj_names, new_shape)
    
    def hideObj(self, hide=True):
        """Edit whether or not an object is hidden in the entire series.
        
            Params:
                hide (bool): True if the object should be hidden
        """
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return
        
        self.manager.hideObjects(obj_names, hide)

    def addTo3D(self):
        """Generate a 3D view of an object"""
        obj_names = self.getSelectedObjects()
        if obj_names:
            self.mainwindow.addTo3D(obj_names)
    
    def remove3D(self):
        """Remove object(s) from the scene."""
        obj_names = self.getSelectedObjects()
        if obj_names:
            self.mainwindow.removeFrom3D(obj_names)

    def exportAs3D(self, export_type):
        """Export 3D objects."""
        obj_names = self.getSelectedObjects()
        if obj_names:
            self.mainwindow.exportAs3D(obj_names, export_type)

    def addToGroup(self, log_event=True):
        """Add objects to a group."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return
        
        # ask the user for the group
        group_name, confirmed = ObjectGroupDialog(self, self.series.object_groups).exec()

        if not confirmed:
            return
        
        self.series_states.addState()
        
        for name in obj_names:
            self.series.object_groups.add(group=group_name, obj=name)
            if log_event:
                self.series.addLog(name, None, f"Add to group '{group_name}'")
        
        self.manager.updateObjects(obj_names)

    
    def removeFromGroup(self, log_event=True):
        """Remove objects from a group."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return
        
        # ask the user for the group
        group_name, confirmed = ObjectGroupDialog(self, self.series.object_groups, new_group=False).exec()

        if not confirmed:
            return
        
        self.series_states.addState()
        
        for name in obj_names:
            self.series.object_groups.remove(group=group_name, obj=name)
            if log_event:
                self.series.addLog(name, None, f"Remove from group '{group_name}'")
        
        self.manager.updateObjects(obj_names)
    
    def removeFromAllGroups(self, log_event=True):
        """Remove a set of traces from all groups."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return
        
        self.series_states.addState()
        
        for name in obj_names:
            self.series.object_groups.removeObject(name)
            if log_event:
                self.series.addLog(name, None, f"Remove from all object groups")
            
        self.manager.updateObjects(obj_names)
    
    def removeAllTags(self):
        """Remove all tags from all traces on selected objects."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return
                
        self.manager.removeAllTraceTags(obj_names)
    
    def viewHistory(self):
        """View the history for a set of objects."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return
        
        HistoryTableWidget(self.series.getFullHistory(), self.mainwindow, obj_names)
    
    def createZtrace(self, cross_sectioned=True):
        """Create a ztrace from selected objects."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return
        self.manager.createZtrace(obj_names, cross_sectioned)

    def deleteObjects(self):
        """Delete an object from the entire series."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return
        
        # SPECIAL CASE: this can be accessed be a keyboard shortcut and bypass the initial check
        if self.checkLocked(obj_names):
            return
        
        self.manager.deleteObjects(obj_names)

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
        self.series.setOption("object_columns", self.columns)
        
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
    
    def setREFilter(self):
        """Set a new regex filter for the list."""
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
    
    def setGroupFilter(self):
        """Set a new group filter for the list."""
        structure = [
            ["Enter the group filter(s) below"],
            [("multitext", self.group_filters)]
        ]
        response, confirmed = QuickDialog.get(self, structure, "Group Filters")
        if not confirmed:
            return
        
        self.group_filters = set(response[0])
        
        self.manager.updateTable(self)
    
    def setTagFilter(self):
        """Set a new tag filter for the list."""
        # get a new filter from the user
        structure = [
            ["Enter the tag filter(s) below"],
            [("multitext", self.tag_filters)]
        ]
        response, confirmed = QuickDialog.get(self, structure, "Tag Filters")
        if not confirmed:
            return
        
        self.tag_filters = set(response[0])
        
        # call through manager to update self
        self.manager.updateTable(self)
    
    def setCRFilter(self):
        """Set the filter for curation."""
        structure = [
            ["Curation status:"],
            [(
                "check",
                *((s,c) for s, c in self.cr_status_filter.items())
            )],
            ["Users:"],
            [("multitext", self.cr_user_filters)]
        ]
        response, confirmed = QuickDialog.get(self, structure, "Curation Filters")
        if not confirmed:
            return
        
        self.cr_status_filter = dict(response[0])
        self.cr_user_filters = set(response[1])

        # call through manager to update self
        self.manager.updateTable(self)
    
    def findFirst(self, event=None):
        """Focus the field on the first occurence of an object in the series."""
        obj_name = self.getSelectedObject()
        if obj_name is None:
            return
        self.manager.findObject(obj_name, first=True)
    
    def findLast(self):
        """Focus the field on the last occurence of an object in the series."""
        obj_name = self.getSelectedObject()
        if obj_name is None:
            return
        self.manager.findObject(obj_name, first=False)
    
    def edit3D(self):
        """Edit the 3D options for an object or set of objects."""
        obj_names = self.getSelectedObjects()
        if not obj_names:
            return
        
        # check for object names and opacities
        type_3D = self.series.getAttr(obj_names[0], "3D_mode")
        opacity = self.series.getAttr(obj_names[0], "3D_opacity")
        for name in obj_names[1:]:
            new_type = self.series.getAttr(name, "3D_mode")
            new_opacity = self.series.getAttr(name, "3D_opacity")
            if type_3D != new_type:
                type_3D = None
            if opacity != new_opacity:
                opacity = None
        
        structure = [
            ["3D Type:", ("combo", ["surface", "spheres", "contours"], type_3D)],
            ["Opacity (0-1):", ("float", opacity, (0,1))]
        ]
        response, confirmed = QuickDialog.get(self, structure, "3D Object Settings")
        if not confirmed:
            return
        
        new_type, new_opacity = response

        self.manager.edit3D(obj_names, new_type, new_opacity)
    
    def bulkCurate(self, curation_status : str):
        """Set the curation status for multiple selected objects.
        
            Params:
                curation_status (str): "", "Needs curation" or "Curated"
        """
        names = self.getSelectedObjects()
        if not names:
            return
        
        # prompt assign to
        if curation_status == "Needs curation":
            assign_to, confirmed = QInputDialog.getText(
                self,
                "Assign to",
                "Assign curation to username:\n(press enter to leave blank)"
            )
            if not confirmed:
                return
        else:
            assign_to = ""
        
        self.series_states.addState()
        
        self.series.setCuration(names, curation_status, assign_to)
        self.manager.updateObjects(names)
        self.mainwindow.seriesModified(True)
    
    def renameGroup(self):
        """Rename an object group."""
        structure = [
            ["Group:", (True, "combo", self.series.object_groups.getGroupList())],
            ["New name:", (True, "text", "")]
        ]
        response, confirmed = QuickDialog.get(self, structure, "Rename Group")
        if not confirmed:
            return
        
        group = response[0]
        new_group = response[1]
        if new_group in self.series.object_groups.getGroupList():
            notify("This group already exists.")
            return
        
        self.series_states.addState()

        objs_to_update = self.series.object_groups.getGroupObjects(group).copy()
        self.series.object_groups.renameGroup(group, new_group)
        self.manager.updateObjects(objs_to_update)
    
    def deleteGroup(self):
        """Delete an object group."""
        structure = [
            ["Group:", (True, "combo", self.series.object_groups.getGroupList())]
        ]
        response, confirmed = QuickDialog.get(self, structure, "Delete Group")
        if not confirmed:
            return
        
        self.series_states.addState()
        
        group = response[0]
        if group in self.series.object_groups.getGroupList():
            objs_to_update = self.series.object_groups.getGroupObjects(group).copy()
            self.series.object_groups.removeGroup(group)
            self.manager.updateObjects(objs_to_update)
    
    def lockObjects(self, lock=True):
        """Locked the selected objects."""
        names = self.getSelectedObjects()

        self.series_states.addState()

        for name in names:
            self.series.setAttr(name, "locked", lock)

        self.manager.updateObjects(names)
        self.mainwindow.field.deselectAllTraces()
    
    def setPalette(self):
        """Set the selected object name as the name of the selected palette trace."""
        name = self.getSelectedObject()
        if not name:
            return
        
        self.mainwindow.setPaletteButtonFromObj(name)
    
    def splitObject(self):
        """Split an object into one object per trace."""
        name = self.getSelectedObject()
        if not name:
            return
        
        self.manager.splitObject(name)
    
    def closeEvent(self, event):
        """Remove self from manager table list."""
        self.manager.tables.remove(self)
        super().closeEvent(event)

