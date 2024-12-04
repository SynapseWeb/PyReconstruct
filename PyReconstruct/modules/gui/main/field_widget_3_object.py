from .context_menu_list import get_context_menu_list_obj

from PySide6.QtWidgets import (
    QInputDialog,
    QMessageBox,
)

from PyReconstruct.modules.datatypes import Transform
from PyReconstruct.modules.gui.dialog import (
    QuickDialog,
    TraceDialog,
    ShapesDialog,
    ObjectGroupDialog,
)
from PyReconstruct.modules.gui.popup import (
    TextWidget,
)
from PyReconstruct.modules.gui.utils import (
    notify
)
from PyReconstruct.modules.gui.table import (
    HistoryTableWidget,
    ObjectTableWidget,
    getCopyTableWidget
)


from .field_widget_2_trace import FieldWidgetTrace


class FieldWidgetObject(FieldWidgetTrace):
    """
    OBJECT FUNCTIONS
    ----------------
    All field functions associated with modifying objects.
    """

    def getObjMenu(self):
        """Get the context menu list for modifying objects."""
        return get_context_menu_list_obj(self)

    # repeated code that individual functions might need to handle:
    #  - any series_states handling
    #  - updating the host tree of an object
    #  - updating any other related objects that are not selected
    #  - refreshing the entire table
    def object_function(update_objects: bool, reload_field: bool):
        """Wrapper for functions on objects that are accessible through both the field and the object list.
        
        Handles determining the object names to pass to its functions and saving the mainwindow data.
        
        Handles reloading and updating the objects in the tables.
        """
        def decorator(fn):
            def wrapper(self, *args, **kwargs):

                ## Get selected names
                vscroll = None  # scroll bar if object list
                data_table = self.table_manager.hasFocus()

                if isinstance(data_table, ObjectTableWidget):
                    selected_names = data_table.getSelected()
                    vscroll = data_table.table.verticalScrollBar()  # track scroll bar position
                    scroll_pos = vscroll.value()
                
                else:
                    selected_names = list(
                        set(t.name for t in self.section.selected_traces)
                    )
                    
                ## If no selected objects
                if not selected_names:
                    return
                
                ## Check for locked objects
                if update_objects:
                    for n in selected_names:
                        if self.series.getAttr(n, "locked"):
                            notify(
                                "Cannot modify locked objects.\n"
                                "Please unlock before modifying."
                            )
                            return
                
                # save the data in the field
                self.mainwindow.saveAllData()

                # call function with selected names inserted
                completed = fn(self, selected_names, *args, **kwargs)

                if not completed:
                    return

                # call to update objects
                if update_objects:
                    self.table_manager.updateObjects(selected_names)
                    self.mainwindow.seriesModified(True)
                
                # reset the scroll bar position if applicable
                if vscroll: vscroll.setValue(scroll_pos)

                if reload_field:
                    self.reload()
                    self.mainwindow.seriesModified(True)
            
            return wrapper
        
        return decorator
    
    def getSingleName(self, obj_names : list):
        """Check that the list of objects has only one object and return it."""
        if len(obj_names) == 0:
            return
        elif len(obj_names) == 1:
            return obj_names[0]
        else:
            notify("Please select only one object for this action.")
            return

    @object_function(update_objects=True, reload_field=True)
    def editAttributes(self, obj_names : list):
        """Edit the name of object(s) in the entire series."""
        
        ## Query user for new object name
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
            return False
        
        attr_trace, sections = response

        ## Modify object on every section
        t = attr_trace

        name, color, tags, mode = (
            t.name, t.color, t.tags, t.fill_mode
        )

        self.series.editObjectAttributes(
            obj_names,
            name,
            color,
            tags,
            mode,
            sections,
            series_states=self.series_states
        )

        ## Decorator will not know to update new name and host trees if name is changed
        if name:
            self.table_manager.updateObjects(
                self.series.host_tree.getObjToUpdate([name] + obj_names)
            )
                
        return True

    @object_function(update_objects=True, reload_field=True)
    def smoothObject(self, obj_names: list):
        """Smooth object traces."""

        self.series_states.addState()

        self.series.smoothObject(
            obj_names,
            series_states=self.series_states
        )

        return True
    
    @object_function(update_objects=True, reload_field=False)
    def editComment(self, obj_names : list):
        """Edit the comment of the object."""
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
            return False
        
        self.series_states.addState()
        
        for obj_name in obj_names:
            self.series.setAttr(obj_name, "comment", new_comment)
            self.series.addLog(obj_name, None, "Edit object comment")

        return True        

    @object_function(update_objects=True, reload_field=False)
    def editAlignment(self, obj_names : list):
        """Edit alignment for object(s)."""
        structure = [
            ["Alignment:", ("combo", list(self.mainwindow.field.section.tforms.keys()))]
        ]
        response, confirmed = QuickDialog.get(self, structure, "Object Alignment")
        if not confirmed:
            return False
        
        self.series_states.addState()
        
        alignment = response[0]
        if not alignment: alignment = None
        for obj_name in obj_names:
            self.series.setAttr(obj_name, "alignment", alignment)
            self.series.addLog(obj_name, None, "Edit default alignment")
        
        self.table_manager.refresh()

        return True
    
    @object_function(update_objects=True, reload_field=True)
    def editRadius(self, obj_names : list):
        """Modify the radius of the trace on an entire object."""
        new_rad, confirmed = QInputDialog.getText(
            self, 
            "Object Trace Radius",
            "Enter the new radius:",
        )
        if not confirmed:
            return False

        try:
            new_rad = float(new_rad)
        except ValueError:
            return False
        
        if new_rad <= 0:
            return False
        
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
                    return False
                
        # iterate through all sections
        self.series.editObjectRadius(
            obj_names,
            new_rad,
            self.series_states
        )

        return True
    
    @object_function(update_objects=True, reload_field=True)
    def editShape(self, obj_names : list):
        """Modify the shape of the traces on an entire object."""
        new_shape, confirmed = ShapesDialog(self).exec()
        if not confirmed:
            return False

        # iterate through all sections
        self.series.editObjectShape(
            obj_names,
            new_shape,
            self.series_states
        )

        return True
    
    @object_function(update_objects=True, reload_field=True)
    def hideObj(self, obj_names : list, hide=True):
        """Edit whether or not an object is hidden in the entire series.
        
            Params:
                hide (bool): True if the object should be hidden
        """
        # iterate through sections and hide the traces
        self.series.hideObjects(obj_names, hide, self.series_states)

        return True

    @object_function(update_objects=False, reload_field=False)
    def addTo3D(self, obj_names : list):
        """Generate a 3D view of an object"""
        self.mainwindow.addTo3D(obj_names)
    
    @object_function(update_objects=False, reload_field=False)
    def remove3D(self, obj_names : list):
        """Remove object(s) from the scene."""
        self.mainwindow.removeFrom3D(obj_names)

    @object_function(update_objects=False, reload_field=False)
    def exportAs3D(self, obj_names : list, export_type):
        """Export 3D objects."""
        self.mainwindow.exportAs3D(obj_names, export_type)

    @object_function(update_objects=True, reload_field=False)
    def addToGroup(self, obj_names : list, log_event=True):
        """Add objects to a group."""

        obj_groups = self.series.object_groups
        starting_groups = obj_groups.getGroupList()
        
        # ask the user for the group
        group_name, confirmed = ObjectGroupDialog(self, obj_groups).exec()

        if not confirmed:
            return False
        
        self.series_states.addState()
        
        for name in obj_names:
            
            obj_groups.add(group=group_name, obj=name)
            
            if log_event:
                self.series.addLog(
                    name, None, f"Add to group '{group_name}'"
                )
        
            ## Update series visibility
            if group_name not in starting_groups:
                self.series.groups_visibility[group_name] = True

                ## Update menubar
                self.mainwindow.createMenuBar()

        return True
    
    @object_function(update_objects=True, reload_field=False)
    def removeFromGroup(self, obj_names : list, log_event=True):
        """Remove objects from a group."""
        # ask the user for the group

        obj_groups = self.series.object_groups
        starting_groups = obj_groups.getGroupList()
        
        group_name, confirmed = ObjectGroupDialog(
            self, obj_groups, new_group=False
        ).exec()

        if not confirmed:
            return False
        
        self.series_states.addState()

        for name in obj_names:
            
            obj_groups.remove(group=group_name, obj=name)
            
            if log_event:
                self.series.addLog(
                    name, None, f"Remove from group '{group_name}'"
                )

            ## Update group visibility
            if group_name not in obj_groups.getGroupList():
                del self.series.groups_visibility[group_name]
            
                ## Create menubar
                self.mainwindow.createMenuBar()

        return True

    @object_function(update_objects=True, reload_field=False)    
    def removeFromAllGroups(self, obj_names : list, log_event=True):
        """Remove a set of traces from all groups."""
        self.series_states.addState()

        obj_groups = self.series.object_groups
        starting_groups = obj_groups.getGroupList()
        
        for name in obj_names:
            
            obj_groups.removeObject(name)
            
            if log_event:
                self.series.addLog(
                    name, None, f"Remove from all object groups"
                )

        ## Update group visibility
        group_diffs = set(starting_groups) - set(obj_groups.getGroupList())
        if group_diffs:

            ## Loop over each group that differs and rm from group viz
            for diff in group_diffs:
                del self.series.groups_visibility[diff]
            
            ## Update menubar
            self.mainwindow.createMenuBar()

        return True

    @object_function(update_objects=True, reload_field=True)    
    def removeAllTags(self, obj_names : list):
        """Remove all tags from all traces on selected objects."""    
        # iterate through all the sections
        self.series.removeAllTraceTags(obj_names, self.series_states)

        return True
    
    @object_function(update_objects=False, reload_field=False)
    def viewHistory(self, obj_names : list):
        """View the history for a set of objects."""
        HistoryTableWidget(self.series.getFullHistory(), self.mainwindow, obj_names)
    
    @object_function(update_objects=False, reload_field=True)
    def createZtrace(self, obj_names : list, cross_sectioned=True):
        """Create a ztrace from selected objects."""
        self.series_states.addState()

        for name in obj_names:
            self.series.createZtrace(name, cross_sectioned)
        
        # manual call to update ztraces
        self.mainwindow.field.table_manager.updateZtraces()

        return True

    @object_function(update_objects=True, reload_field=True)
    def deleteObjects(self, obj_names : list):
        """Delete an object from the entire series."""
        # get the objects that will require updating once deleted (include hosted objects)
        modified_objs = self.series.host_tree.getObjToUpdate(obj_names)

        # delete the object on every section
        self.series.deleteObjects(obj_names, self.series_states)

        # update the dictionary data and tables
        self.table_manager.updateObjects(modified_objs)

        return True
    
    @object_function(update_objects=True, reload_field=True)
    def copyObjects(self, obj_names: list):
        """Make copies of object(s)."""

        self.series_states.addState()

        series_states = self.mainwindow.field.series_states
        copies = self.series.copyObjects(obj_names, series_states)

        ## Update dictionary data and tables
        self.table_manager.updateObjects(copies)

        return True

    @object_function(update_objects=False, reload_field=False)
    def edit3D(self, obj_names : list):
        """Edit the 3D options for an object or set of objects."""
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
            return False
        
        new_type, new_opacity = response

        self.series_states.addState()

        # set the series settings
        for name in obj_names:
            if new_type:
                self.series.setAttr(name, "3D_mode", new_type)
            if new_opacity is not None:
                self.series.setAttr(name, "3D_opacity", new_opacity)
        
        # if this object exists in the 3D scene, update its opacity
        if self.mainwindow.viewer:
            for name in obj_names:
                scene_obj = self.mainwindow.viewer.plt.objs.search(
                    name,
                    "object",
                    self.series.jser_fp
                )
                if scene_obj:
                    print("alpha set")
                    scene_obj.setAlpha(new_opacity)
                    
        self.mainwindow.seriesModified(True)
        
        return True
    
    @object_function(update_objects=True, reload_field=False)
    def bulkCurate(self, names : list, curation_status : str):
        """Set the curation status for multiple selected objects.
        
            Params:
                curation_status (str): "", "Needs curation" or "Curated"
        """
        # prompt assign to
        if curation_status == "Needs curation":
            assign_to, confirmed = QInputDialog.getText(
                self,
                "Assign to",
                "Assign curation to username:\n(press enter to leave blank)"
            )
            if not confirmed:
                return False
        else:
            assign_to = ""
        
        self.series_states.addState()
        
        self.series.setCuration(names, curation_status, assign_to)

        return True
    
    @object_function(update_objects=False, reload_field=False)  # set update objects as False to avoid the lock check
    def lockObjects(self, names : list, lock=True):
        """Locked the selected objects."""
        self.series_states.addState()

        for name in names:
            self.series.setAttr(name, "locked", lock)

        self.table_manager.updateObjects(names)
        self.mainwindow.field.deselectAllTraces()
        self.mainwindow.seriesModified(True)

        return True
    
    @object_function(update_objects=True, reload_field=True)
    def setPaletteButtonFromObj(self, names : list):
        """Set the selected object name as the name of the selected palette trace."""
        name = self.getSingleName(names)
        if not name:
            return False
        
        self.mainwindow.setPaletteButtonFromObj(name)

        return True
    
    @object_function(update_objects=True, reload_field=True)
    def splitObject(self, names : list):
        """Split an object into one object per trace."""
        name = self.getSingleName(names)
        if not name:
            return False
        
        self.series_states.addState()

        series_states = self.mainwindow.field.series_states
        new_names = self.series.splitObject(name, series_states)

        self.table_manager.updateObjects(new_names)  # manual call to update the objects

        return True

    @object_function(update_objects=True, reload_field=False)
    def setUserCol(self, names : list, col_name : str, opt : str, log_event=True):
        """Set the categorical user column for an object.
        
            Params:
                col_name (str): the name of the user-defined column
                opt (str): the option to set for the object(s)
        """
        self.series_states.addState()

        for name in names:
            self.series.setUserColAttr(name, col_name, opt)
        
        if log_event:
            for name in names:
                self.series.addLog(name, None, f"Set user column {col_name} as {opt}")

        return True
    
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

        self.mainwindow.seriesModified(True)
        self.mainwindow.createContextMenus()

        self.table_manager.updateObjCols()

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

        if name in self.series.getOption("object_columns"):
            notify("This column already exists.")
            return
        
        self.series_states.addState()
        self.series.addUserCol(name, opts)

        self.mainwindow.seriesModified(True)
        self.mainwindow.createContextMenus()

        self.table_manager.updateObjCols()

    @object_function(update_objects=False, reload_field=False)    
    def displayHostTree(self, names : list, hosts=True):
        """Display the hosts/travelers of an object in ASCII tree representation.
        
            Params:
                hosts (bool): True if hosts, False if travelers
        """
        name = self.getSingleName(names)
        if not name:
            return False
        
        t = TextWidget(
            self.mainwindow,
            self.series.host_tree.getASCII(name, hosts),
            "Host Tree" if hosts else "Inhabitant Tree",
        )
        t.output.setFont("Courier New")

        return True
    
    @object_function(update_objects=True, reload_field=False)
    def setHosts(self, names : list):
        """Set host(s) for selected object(s)."""
        if len(names) == 1:
            current_hosts = self.series.getObjHosts(names[0])
        else:
            current_hosts = []
        
        structure = [
            ["Host Name:"],
            [(True, "multicombo", list(self.series.data["objects"].keys()), current_hosts)]
        ]
        response, confirmed = QuickDialog.get(self, structure, "Object Host")
        if not confirmed:
            return False
        host_names = list(set(response[0]))
        
        ## Ensure objects do not host each other
        for hn in host_names:
            
            if hn in names:
                notify("An object cannot host itself.")
                return False

            ## If intersection exists
            trav_hosts = set(self.series.getObjHosts(hn, traverse=True))
            if bool(set(names) & trav_hosts):
                notify("Objects cannot host each other.")
                return False
        
        self.series_states.addState()
        self.series.setObjHosts(names, host_names)

        ## Explicitly update entire host tree
        self.table_manager.updateObjects(
            self.series.host_tree.getObjToUpdate(names)
        )

        return True
    
    @object_function(update_objects=True, reload_field=False)
    def clearHosts(self, names : list):
        """Clear the host(s) for the selected object(s)."""
        self.series_states.addState()
        self.series.clearObjHosts(names)
        
        # manual call to update entire host tree
        self.table_manager.updateObjects(
            self.series.host_tree.getObjToUpdate(names)
        )

        return True

    
