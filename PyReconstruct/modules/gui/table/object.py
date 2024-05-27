import re

from PySide6.QtWidgets import (
    QTableWidgetItem,  
    QWidget, 
    QInputDialog, 
    QMenu, 
    QApplication,
    QMessageBox,
)
from PySide6.QtGui import (
    QPalette,
    QColor
)
from PySide6.QtCore import Qt

from .data_table import DataTable
from .history import HistoryTableWidget
from .str_helper import sortList

from PyReconstruct.modules.datatypes import Series
from PyReconstruct.modules.gui.utils import (
    populateMenuBar,
    populateMenu,
    notify,
)
from PyReconstruct.modules.gui.dialog import (
    ObjectGroupDialog,
    TraceDialog,
    ShapesDialog,
    QuickDialog,
)

class ObjectTableWidget(DataTable):

    def __init__(self, series : Series, mainwindow : QWidget, manager):
        """Create the object table dock widget.
        
            Params:
                series (Series): the Series object
                mainwindow (MainWindow): the main window the dock is connected to
                manager: the object table manager
        """
        # set the filter defaults
        self.re_filters = set([".*"])
        self.tag_filters = set()
        self.group_filters = set()
        self.cr_status_filter = {
            "Blank": True,
            "Needs curation": True,
            "Curated": True
        }
        self.cr_user_filters = set()
        self.user_col_filters = {}

        super().__init__("object", series, mainwindow, manager)
        self.static_columns = ["Name"]
        self.createTable()

        self.show()
    
    def createMenus(self):
        """Create the menu for the object table widget."""
        # get the actions to edit the user columns
        def getCall(col_name):
            return (lambda : self.editUserCol(col_name=col_name))
        edit_user_cols = []
        n = 0
        for col_name in self.series.user_columns:
            edit_user_cols.append(
                (f"edit_user_col_{n}_act", col_name, "", getCall(col_name))
            )
        
        # create the submenu for adding categorical column filters
        def getCall(col_name, opt_name):
            return (lambda : self.toggleUserColFilter(
                col_name=col_name, 
                opt_name=opt_name, 
            ))
        filter_submenus = [
            ("clearusercolfilters_act", "Clear all", "", self.clearUserColFilters)
        ]
        menu_i = 0  # keep track of numbers for unique attribute
        opts_i = 0
        for col_name, opts in self.series.user_columns.items():
            d = {
                "attr_name": f"filter_user_col_{menu_i}_menu",
                "text": col_name,
                "opts": []
            }
            menu_i += 1
            for opt in opts:
                cb_str = "checkbox"
                if col_name in self.user_col_filters and opt in self.user_col_filters[col_name]:
                    cb_str += "-True"
                d["opts"].append(
                    (f"filter_user_col_{opts_i}_act", opt, cb_str, getCall(col_name, opt))
                )
                opts_i += 1
            filter_submenus.append(d)

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
                    ("crstatusfilter_act", "Curation filter...", "", self.setCRFilter),
                    {
                        "attr_name": "usercolfiltersmenu",
                        "text": "Categorical column filters",
                        "opts": filter_submenus
                    }
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
            },
            {
                "attr_name": "columnsmenu",
                "text": "Columns",
                "opts":
                [
                    ("columns_act", "Set columns...", "", self.setColumns),
                    None,
                    ("addcolumn_act", "Create categorical column...", "", self.addUserCol),
                    ("removecolumn_act", "Delete categorical column...", "", self.removeUserCol),
                    None,
                    {
                        "attr_name": "editcolumn_menu",
                        "text": "Edit column",
                        "opts": edit_user_cols
                    }
                ]
            }
        ]
        # create the menubar object
        self.menubar = self.main_widget.menuBar()
        self.menubar.clear()
        self.menubar.setNativeMenuBar(False) # attach menu to the window
        # fill in the menu bar object
        populateMenuBar(self, self.menubar, menubar_list)

        # create the submenu for adding to categorical column
        def getCall(col_name, opt):
            return (lambda : self.setUserCol(col_name=col_name, opt=opt))
        custom_categories = []
        menu_i = 0  # keep track of numbers for unique attribute
        opts_i = 0
        for col_name, opts in self.series.user_columns.items():
            d = {
                "attr_name": f"user_col_{menu_i}_menu",
                "text": col_name,
                "opts":
                [
                    (f"user_col_{opts_i}_act", "(blank)", "", getCall(col_name, ""))
                ]
            }
            menu_i += 1
            opts_i += 1
            for opt in opts:
                d["opts"].append(
                    (f"user_col_{opts_i}_act", opt, "", getCall(col_name, opt))
                )
                opts_i += 1
            custom_categories.append(d)

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
                "attr_name": "customcatmenu",
                "text": "Custom categories",
                "opts": custom_categories
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
        is_cr = dict(self.columns)["Curate"] and (
            bool(self.cr_user_filters) or not all(self.cr_status_filter.values())
        )
        is_user_col = bool(self.user_col_filters)

        title = "Object List "
        if any((is_regex, is_tag, is_group, is_cr, is_user_col)):
            strs = []
            if is_regex: strs.append("regex")
            if is_tag: strs.append("tags")
            if is_group: strs.append("groups")
            if is_cr: strs.append("curation")
            if is_user_col: strs.append("categorical columns")
            title += f"(Filtered by: {', '.join(strs)})"
        
        self.setWindowTitle(title)
    
    def getHeaders(self):
        """Get the headers for the table."""
        self.curate_column = None
        h = ["Name"]
        for key, b in self.columns:
            if b and key == "Range":
                h.append("Start")
                h.append("End")
            elif b and key == "Curate":
                self.curate_column = len(h)
                h.append("CR")
                h.append("Status")
                h.append("User")
                h.append("Date")
            elif b:
                h.append(key)
        return h
    
    def getItems(self, name : str, item_type : str):
        """Get the QTableWidgetItem(s) for an attribute of an object.
        
            Params:
                name (str): the name of the object to retrieve the data for
                item_type (str): the specific data to be retrieved
        """
        items = []
        if item_type == "Name":
            items.append(QTableWidgetItem(name))
        elif item_type == "Range":
            items.append(QTableWidgetItem(str(self.series.data.getStart(name))))
            items.append(QTableWidgetItem(str(self.series.data.getEnd(name))))
        elif item_type == "Count":
            items.append(QTableWidgetItem(str(self.series.data.getCount(name))))
        elif item_type == "Flat area":
            items.append(QTableWidgetItem(str(round(self.series.data.getFlatArea(name), 5))))
        elif item_type == "Volume":
            items.append(QTableWidgetItem(str(round(self.series.data.getVolume(name), 5))))
        elif item_type == "Radius":
            items.append(QTableWidgetItem(str(round(self.series.data.getAvgRadius(name), 5))))
        elif item_type == "Groups":
            groups = self.series.object_groups.getObjectGroups(name)
            groups_str = ", ".join(groups)
            items.append(QTableWidgetItem(groups_str))
        elif item_type == "Trace tags":
            tags = self.series.data.getTags(name)
            tags_str = ", ".join(tags)
            items.append(QTableWidgetItem(tags_str))
        elif item_type == "Locked":
            item = QTableWidgetItem("")
            item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            item.setCheckState(Qt.CheckState.Checked if self.series.getAttr(name, "locked") else Qt.CheckState.Unchecked)
            items.append(item)
        elif item_type == "Last user":
            last_user = self.series.getAttr(name, "last_user")
            items.append(QTableWidgetItem(last_user))
        elif item_type == "Curate":
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
                text_lightness = QApplication.palette().color(QPalette.WindowText).lightness()
                if curated:
                    check_item.setCheckState(Qt.CheckState.Checked)
                    status_item.setText("Curated")
                    cr_color = Qt.blue if text_lightness > 128 else Qt.cyan
                else:
                    check_item.setCheckState(Qt.CheckState.PartiallyChecked)
                    status_item.setText(f"Needs curation")
                    cr_color = QColor(100, 100, 0) if text_lightness > 128 else Qt.yellow
                user_item.setText(user)
                date_item.setText(date)
            for item in cr_items:
                if cr_color:
                    item.setData(Qt.BackgroundRole, cr_color)
                    item.setBackground(cr_color)
                items.append(item)
        elif item_type == "Alignment":
            alignment = self.series.getAttr(name, "alignment")
            if alignment is None: alignment = ""
            items.append(QTableWidgetItem(alignment))
        elif item_type == "Comment":
            comment = self.series.getAttr(name, "comment")
            items.append(QTableWidgetItem(comment))
        elif item_type in self.series.user_columns:
            value = self.series.getUserColAttr(name, item_type)
            if value is None: value = ""
            items.append(QTableWidgetItem(value))
        
        return items
    
    def passesFilters(self, name : str):
        """Check if an object passes the filters.
        
            Params:
                name (str): the name of the object
        """
        # check user columns
        if self.user_col_filters:
            passes_filters = False
            for n, value in self.series.getAttr(name, "user_columns").items():
                if n in self.user_col_filters and value in self.user_col_filters[n]:
                    passes_filters = True
                    break
            if not passes_filters:
                return False

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
        if dict(self.columns)["Curate"]:
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

    def getFiltered(self):
        """Get the names of the objects that pass the filter.
        
            Params:
                obj_name_list (list): the list of object names
        """
        filtered_list = super().getFiltered(
            list(self.series.data["objects"].keys())
        )
        return sortList(filtered_list)
    
    def updateData(self, names : list):
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
    
    def getSelected(self, single=False):
        """Get the name of the objects highlighted by the user.
            Params:
                single (bool): True if only accept single selection
            Returns:
                (str | list): the object name(s)
        """
        selected_indexes = self.table.selectedIndexes()
        obj_names = []
        for i in selected_indexes:
            r = i.row()
            n = self.table.item(r, 0).text()
            obj_names.append(n)

        self.checkLocked(obj_names)
        
        if single:
            if len(obj_names) != 1:
                notify("Please select only one object for this option.")
                return
            else:
                return obj_names[0]
        else:
            return obj_names

    def itemChanged(self, item : QTableWidgetItem):
        """User checked a checkbox."""
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
    
    def editAttributes(self):
        """Edit the name of an object in the entire series."""
        obj_names = self.getSelected()
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
        obj_names = self.getSelected()
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
        self.updateData(obj_names)

        self.mainwindow.seriesModified(True)
    
    def editAlignment(self):
        """Edit alignment for object(s)."""
        obj_names = self.getSelected()
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
        obj_names = self.getSelected()
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
        obj_names = self.getSelected()
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
        obj_names = self.getSelected()
        if not obj_names:
            return
        
        self.manager.hideObjects(obj_names, hide)

    def addTo3D(self):
        """Generate a 3D view of an object"""
        obj_names = self.getSelected()
        if obj_names:
            self.mainwindow.addTo3D(obj_names)
    
    def remove3D(self):
        """Remove object(s) from the scene."""
        obj_names = self.getSelected()
        if obj_names:
            self.mainwindow.removeFrom3D(obj_names)

    def exportAs3D(self, export_type):
        """Export 3D objects."""
        obj_names = self.getSelected()
        if obj_names:
            self.mainwindow.exportAs3D(obj_names, export_type)

    def addToGroup(self, log_event=True):
        """Add objects to a group."""
        obj_names = self.getSelected()
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
        obj_names = self.getSelected()
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
        obj_names = self.getSelected()
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
        obj_names = self.getSelected()
        if not obj_names:
            return
                
        self.manager.removeAllTraceTags(obj_names)
    
    def viewHistory(self):
        """View the history for a set of objects."""
        obj_names = self.getSelected()
        if not obj_names:
            return
        
        HistoryTableWidget(self.series.getFullHistory(), self.mainwindow, obj_names)
    
    def createZtrace(self, cross_sectioned=True):
        """Create a ztrace from selected objects."""
        obj_names = self.getSelected()
        if not obj_names:
            return
        self.manager.createZtrace(obj_names, cross_sectioned)

    def deleteObjects(self, obj_names=None):
        """Delete an object from the entire series."""
        if obj_names is None:
            obj_names = self.getSelected()
        if not obj_names:
            return
        
        self.manager.deleteObjects(obj_names)
    
    def backspace(self):
        """Called when the user hits backspace."""
        obj_names = self.getSelected()
        if not obj_names:
            return
        
        if self.checkLocked(obj_names):
            return
        
        self.deleteObjects()
    
    def edit3D(self):
        """Edit the 3D options for an object or set of objects."""
        obj_names = self.getSelected()
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

        self.mainwindow.seriesModified(True)
    
    def bulkCurate(self, curation_status : str):
        """Set the curation status for multiple selected objects.
        
            Params:
                curation_status (str): "", "Needs curation" or "Curated"
        """
        names = self.getSelected()
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
    
    def lockObjects(self, lock=True):
        """Locked the selected objects."""
        names = self.getSelected()

        self.series_states.addState()

        for name in names:
            self.series.setAttr(name, "locked", lock)

        self.manager.updateObjects(names)
        self.mainwindow.field.deselectAllTraces()

        self.mainwindow.seriesModified(True)
    
    def setPalette(self):
        """Set the selected object name as the name of the selected palette trace."""
        name = self.getSelected(single=True)
        if not name:
            return
        
        self.mainwindow.setPaletteButtonFromObj(name)
    
    def splitObject(self):
        """Split an object into one object per trace."""
        name = self.getSelected(single=True)
        if not name:
            return
        
        self.manager.splitObject(name)
    
    def setUserCol(self, col_name : str, opt : str, log_event=True):
        """Set the categorical user column for an object.
        
            Params:
                col_name (str): the name of the user-defined column
                opt (str): the option to set for the object(s)
        """
        names = self.getSelected()
        if not names:
            return
        
        self.series_states.addState()

        for name in names:
            self.series.setUserColAttr(name, col_name, opt)
        
        if log_event:
            for name in names:
                self.series.addLog(name, None, f"Set user column {col_name} as {opt}")
        
        self.updateData(names)

        self.mainwindow.seriesModified(True)

    # MENU-RELATED FUNCTIONS     
    
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
        name = self.getSelected(single=True)
        if not name:
            return

        self.manager.findObject(name, first=True)
    
    def findLast(self):
        """Focus the field on the last occurence of an object in the series."""
        name = self.getSelected(single=True)
        if not name:
            return

        self.manager.findObject(name, first=False)
    
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

        self.mainwindow.seriesModified(True)
    
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
        
        self.mainwindow.seriesModified(True)
    
    def addUserCol(self):
        """Add a user-defined column."""
        structure = [
            ["Column name:"],
            [(True, "text", "")],
            [" "],
            ["Options:"],
            [(True, "multitext", [])]
        ]
        response, confirmed = QuickDialog.get(self, structure, "Add Column")
        if not confirmed:
            return
    
        name = response[0]
        opts = response[1]

        if name in self.columns:
            notify("This column already exists.")
            return
        
        self.series_states.addState()

        self.series.addUserCol(name, opts)
        self.columns = self.series.getOption("object_columns")
        self.manager.updateTable(self)
        self.createMenus()
        self.mainwindow.seriesModified(True)
    
    def removeUserCol(self):
        """Remove a user-defined column."""
        user_col_names = list(self.series.user_columns.keys())
        structure = [
            ["Remove column:"],
            [(True, "combo", user_col_names)]
        ]
        response, confirmed = QuickDialog.get(self, structure, "Remove Column")
        if not confirmed:
            return
        
        self.series_states.addState()
        
        self.series.removeUserCol(response[0])
        self.columns = self.series.getOption("object_columns")
        self.manager.updateTable(self)
        self.createMenus()
        self.mainwindow.seriesModified(True)
    
    def editUserCol(self, col_name : str):
        """Edit a user-defined column.
        
            Params:
                col_name (str): the name of the user-defined column to edit
        """
        structure = [
            ["Column name:"],
            [(True, "text", col_name)],
            [" "],
            ["Options:"],
            [(True, "multitext", self.series.user_columns[col_name])]
        ]
        response, confirmed = QuickDialog.get(self, structure, "Add Column")
        if not confirmed:
            return
        
        name = response[0]
        opts = response[1]

        if name != col_name and name in self.series.user_columns:
            notify("This group already exists.")
            return
        
        self.series_states.addState()
        
        self.series.editUserCol(col_name, name, opts)
        self.columns = self.series.getOption("object_columns")
        self.manager.updateTable(self)
        self.createMenus()
        self.mainwindow.seriesModified(True)
    
    def toggleUserColFilter(self, col_name : str, opt_name : str):
        """Add/remove a user column filter.
        
            Params:
                col_name (str): the name of the user column
                opt_name (str): the name of the option to filter for
        """
        # check if the filter already exists
        if col_name in self.user_col_filters and opt_name in self.user_col_filters[col_name]:
            # remove the option from the list
            self.user_col_filters[col_name].remove(opt_name)
            # remove the dict option if it is empty
            if not self.user_col_filters[col_name]:
                del(self.user_col_filters[col_name])
        else:
            # add the filter
            if col_name not in self.user_col_filters:
                self.user_col_filters[col_name] = []
            self.user_col_filters[col_name].append(opt_name)
        
        # call through manager to update self (action is updated here)
        self.manager.updateTable(self)
    
    def clearUserColFilters(self):
        """Clear the user column filters."""
        self.user_col_filters = {}
        self.manager.updateTable(self)

