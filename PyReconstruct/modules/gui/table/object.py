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
from PyReconstruct.modules.gui.utils import sortList

from PyReconstruct.modules.datatypes import Series
from PyReconstruct.modules.gui.utils import (
    populateMenuBar,
    populateMenu,
    notify,
    getUserColsMenu,
)
from PyReconstruct.modules.gui.dialog import (
    ObjectGroupDialog,
    TraceDialog,
    ShapesDialog,
    QuickDialog,
    FileDialog
)
from PyReconstruct.modules.gui.popup import (
    TextWidget,
)

class ObjectTableWidget(DataTable):
    
    def __init__(self, series : Series, mainwindow : QWidget, manager, hidden=False):
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
        self.config_filters = {
            "closed"         : True,
            "open"           : True,
            "mixed"          : True
        }
        self.cr_status_filter = {
            "Blank"          : True,
            "Needs curation" : True,
            "Curated"        : True
        }
        self.cr_user_filters = set()
        self.user_col_filters = {}
        self.host_filters = set()
        self.direct_hosts_only = False

        super().__init__("object", series, mainwindow, manager)
        self.static_columns = ["Name"]
        self.createTable()

        if hidden:
            self.hide()
        else:
            self.show()
    
    def createMenus(self):
        """Create the menu for the object table widget."""
        # get the actions to edit the user columns
        def getCall(col_name):
            return (
                lambda : self.mainwindow.field.editUserCol(
                    col_name=col_name
                )
            )
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
                    ("configfilter_act", "Configuration filter...", "", self.setConfigurationFilter),
                    ("hostfilter_act", "Host filter...", "", self.setHostFilter),
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
                    ("addcolumn_act", "Create categorical column...", "", self.mainwindow.field.addUserCol),
                    ("removecolumn_act", "Delete categorical column...", "", self.removeUserCol),
                    None,
                    {
                        "attr_name": "editcolumn_menu",
                        "text": "Edit column",
                        "opts": edit_user_cols
                    },
                    None,
                    ("exportcolumns_act", "Export user columns...", "", self.exportUserColText),
                    ("importcolumns_act", "Import user columns...", "", self.importUserColText),
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
        context_menu_list = self.mainwindow.field.getObjMenu()
        self.context_menu = QMenu(self)
        populateMenu(self, self.context_menu, context_menu_list)

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
            
        elif item_type == "Host":
            
            items.append(QTableWidgetItem(", ".join(self.series.getObjHosts(name))))
            
        elif item_type == "Superhosts":
            
            hosts = self.series.getObjHosts(name, True, True)
            items.append(QTableWidgetItem(", ".join(hosts)))
            
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

        elif item_type == "Configuration":

            items.append(
                QTableWidgetItem(
                    self.series.data.getConfiguration(name)
                )
            )
            
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

        ## Return False if obj does not exists
        if name not in self.series.data["objects"]:
            return False
        
        ## Check user columns
        if self.user_col_filters:
            passes_filters = False
            for n, value in self.series.getAttr(name, "user_columns").items():
                if n in self.user_col_filters and value in self.user_col_filters[n]:
                    passes_filters = True
                    break
            if not passes_filters:
                return False

        ## Check groups
        filters_len = len(self.group_filters)
        if filters_len != 0:  # if group filter requested
            object_groups = self.series.object_groups.getObjectGroups(name)
            groups_len = len(object_groups)
            union_len = len(object_groups.union(self.group_filters))
            if union_len == groups_len + filters_len:  # intersection does not exist
                return False
        
        ## Check tags
        filters_len = len(self.tag_filters)
        if filters_len != 0:
            object_tags = self.series.data.getTags(name)
            object_len = len(object_tags)
            union_len = len(object_tags.union(self.tag_filters))
            if union_len == object_len + filters_len:  # intersection does not exist
                return False
        
        ## Check curation status and user
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

        ## Check config
        if dict(self.columns)["Configuration"]:
            
            req_configs = [
                ori for ori, req
                in self.config_filters.items()
                if req == True
            ]

            obj_config = self.series.data.getConfiguration(name)

            if obj_config not in req_configs and obj_config is not None:
                return False
            
        ## Check regex
        passes_filters = False if self.re_filters else True
        for re_filter in self.re_filters:
            if bool(re.fullmatch(re_filter, name)):
                passes_filters = True
        if not passes_filters:
            return False

        # check hosts
        found_host = False if bool(self.host_filters) else True
        if name in self.host_filters:
            found_host = True
        else:
            for host in self.host_filters:
                if host in self.series.getObjHosts(name, not self.direct_hosts_only):
                    found_host = True
        if not found_host:
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

    def createTable(self):
        """Create the table widget."""
        self.updateObjCols(recreate=False)
        super().createTable()
    
    def updateData(self, names : list):
        """Update the data for a set of objects.
        
            Params:
                names (iterable): the names of the objects to update
        """
        for name in names:

            row, exists_in_table = self.table.getRowIndex(name)
            exists_in_series = name in self.series.data["objects"]
            pass_filters = self.passesFilters(name)

            remove = exists_in_table and (not exists_in_series or not pass_filters)

            ## Completely delete object
            if remove:  
                
                self.table.removeRow(row)

            ## Update existing row
            elif exists_in_table and exists_in_series:
                
                self.setRow(name, row)

            ## Add new row
            elif not exists_in_table and exists_in_series and pass_filters:  
                
                self.table.insertRow(row)
                self.setRow(name, row)

        self.mainwindow.checkActions()
    
    def mouseDoubleClickEvent(self, event):
        """Called when user double-clicks."""
        modifiers = QApplication.keyboardModifiers()
        if modifiers == Qt.ShiftModifier:
            self.mainwindow.field.addTo3D()
        else:
            self.findFirst()
    
    # def checkLocked(self, obj_names : list, lock_actions=True):
    #     """Check for locked objects within a list of obj names.
        
    #         Params:
    #             obj_list (list): the names to check
    #             lock_actions (bool): True if actions should be locked if locked object detected
    #     """
    #     locked = False
    #     for name in obj_names:
    #         if self.series.getAttr(name, "locked"):
    #             locked = True
    #             break
        
    #     if lock_actions:
    #         for act_name in self.locked_actions:
    #             getattr(self, act_name).setEnabled(not locked)
        
    #     return locked
    
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

        # self.checkLocked(obj_names)
        
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
    
    def updateObjCols(self, recreate=True):
        """Update the object column options based on the series.user_columns.
        
            Params:
                recreate (bool): True if menus and table should be recreated in the event of a column change
        """
        update_table = False
        default_columns = self.series.getOption("object_columns", get_default=True)

        # column has been removed
        for pair in self.columns.copy():
            col_name, b = pair
            if col_name not in dict(default_columns) and col_name not in self.series.user_columns:
                self.columns.remove(pair)
                update_table |= b
        
        # column has been added
        for col_name in self.series.user_columns:
            if col_name not in dict(self.columns):
                self.columns.append((col_name, True))
                update_table = True
        
        self.series.setOption("object_columns", self.columns)
        
        if recreate:
            self.createMenus()
            self.mainwindow.createContextMenus()
            if update_table:
                self.createTable()
    
    def backspace(self):
        """Called when backspace is pressed."""
        self.mainwindow.field.deleteObjects()

    ############################################################################
    ## Menu-related functions ##################################################
    ############################################################################
    
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
        self.manager.recreateTable(self)
    
    def setGroupFilter(self):
        """Set a new group filter for the list."""
        structure = [
            ["Enter the group filter(s) below"],
            [("multicombo", self.series.object_groups.getGroupList(), self.group_filters)]
        ]
        response, confirmed = QuickDialog.get(self, structure, "Group Filters")
        if not confirmed:
            return
        
        self.group_filters = set(response[0])
        
        self.manager.recreateTable(self)
    
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
        self.manager.recreateTable(self)
    
    def setCRFilter(self):
        """Set the filter for curation."""
        structure = [
            ["Curation status:"],
            [
                (
                    "check",
                    *((s,c) for s, c in self.cr_status_filter.items())
                )
            ],
            ["Users:"],
            [("multitext", self.cr_user_filters)]
        ]
        response, confirmed = QuickDialog.get(self, structure, "Curation Filters")
        if not confirmed:
            return

        print(f"{response = }")
        print(f"{self.cr_status_filter}")
        
        self.cr_status_filter = dict(response[0])
        self.cr_user_filters = set(response[1])

        # call through manager to update self
        self.manager.recreateTable(self)

    def setConfigurationFilter(self):
        """Filter by object config."""
        structure = [
            ["Object configuration:"],
            [
                (
                    "check",
                    *((s,c) for s, c in self.config_filters.items())
                )
            ]
        ]
        
        response, confirmed = QuickDialog.get(
            self, structure, "Configuration Filters"
        )

        if not confirmed:
            return

        self.config_filters = dict(response[0])

        ## Call through manager to update self
        self.manager.recreateTable(self)

    def findFirst(self, event=None):
        """Focus the field on the first occurence of an object in the series."""
        name = self.getSelected(single=True)
        if not name:
            return

        self.mainwindow.saveAllData()
        snum = self.series.data.getStart(name)
        self.mainwindow.setToObject(name, snum)
    
    def findLast(self):
        """Focus the field on the last occurence of an object in the series."""
        name = self.getSelected(single=True)
        if not name:
            return

        self.mainwindow.saveAllData()
        snum = self.series.data.getEnd(name)
        self.mainwindow.setToObject(name, snum)
    
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

        self.manager.updateObjCols()
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
        self.manager.recreateTable(self)
    
    def clearUserColFilters(self):
        """Clear the user column filters."""
        self.user_col_filters = {}
        self.manager.recreateTable(self)
    
    def exportUserColText(self):
        """Export user columns to a text file."""
        out_fp = FileDialog.get(
            "save",
            self,
            "File User Columns Text File",
            "*.txt"
        )
        if not out_fp:
            return
        
        self.series.exportUserColsText(out_fp)
    
    def importUserColText(self):
        """Import user columns from a text file."""
        fp = FileDialog.get(
            "file",
            self,
            "Save User Columns Text File",
            "*.txt"
        )
        if not fp:
            return
        
        self.series.importUserColsText(fp)
        self.updateObjCols()
    
    def setHostFilter(self):
        """Set the host filter."""
        structure = [
            ["Filter by objects with the following host(s):"],
            [("multicombo", list(self.series.data["objects"].keys()), self.host_filters)],
            [("check", ("limit to direct hosts", self.direct_hosts_only))],
        ]
        response, confirmed = QuickDialog.get(self, structure, "Object Host")
        if not confirmed:
            return
        
        self.host_filters = set(response[0])
        self.direct_hosts_only = response[1][0][1]

        self.manager.recreateTable(self)

