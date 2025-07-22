"""Input handling operations."""

from PySide6.QtWidgets import QApplication, QMessageBox

from PyReconstruct.modules.gui.dialog import GridDialog, QuickDialog


class HandlingOperations:

    def checkActions(self, context_menu=False, clicked_trace=None, clicked_label=None):
        """Define enabled and disabled actions based on field context.
        
            Params:
                context_menu (bool): True if context menu is being generated
                clicked_trace (Trace): the trace that was clicked on IF the cotext menu is being generated
        """
        ## Skip if actions not initialized
        if not self.actions_initialized:
            return

        field_section = self.field.section
        selected_traces = field_section.selected_traces
        selected_ztraces = field_section.selected_ztraces
        
        ## Allow only general field options if
        ##   1. both traces and z traces highlighted or
        ##   2. nothing highlighted
        
        if not (bool(selected_traces) ^ bool(selected_ztraces)):
            
            for a in self.trace_actions:
                a.setEnabled(False)

            for a in self.ztrace_actions:
                a.setEnabled(False)
                
        ## If selected trace in highlighted traces
        
        elif (
                (not context_menu and selected_traces) or
                (context_menu and clicked_trace in selected_traces)
        ):
            
            for a in self.ztrace_actions:
                a.setEnabled(False)
                
            for a in self.trace_actions:
                a.setEnabled(True)
                
        ## If selected ztrace in highlighted ztraces
        
        elif (
                (not context_menu and field_section.selected_ztraces) or
                (context_menu and clicked_trace in field_section.selected_ztraces)
        ):
            
            for a in self.trace_actions:
                a.setEnabled(False)
                
            for a in self.ztrace_actions:
                a.setEnabled(True)
            
        else:
            
            for a in self.trace_actions:
                a.setEnabled(False)
                
            for a in self.ztrace_actions:
                a.setEnabled(False)

        # check labels
        if clicked_label:
            
            if clicked_label in self.field.zarr_layer.selected_ids:

                self.importlabels_act.setEnabled(True)

                if len(self.zarr_layer.selected_ids) > 1:
                    self.mergelabels_act.setEnabled(True)
                    
            else:
                
                self.importlabels_act.setEnabled(False)
                self.mergelabels_act.setEnabled(False)
        
        #### Menubar ###############################################################################

        ## Disable saving welcome series
        is_not_welcome_series = not self.series.isWelcomeSeries()
        self.save_act.setEnabled(is_not_welcome_series)
        self.saveas_act.setEnabled(is_not_welcome_series)
        self.backupmenu.setEnabled(is_not_welcome_series)

        ## Check for palette
        self.togglepalette_act.setChecked(not self.mouse_palette.palette_hidden)
        self.toggleinc_act.setChecked(not self.mouse_palette.inc_hidden)
        self.togglebc_act.setChecked(not self.mouse_palette.bc_hidden)
        self.togglesb_act.setChecked(not self.mouse_palette.sb_hidden)

        ## Group visibility
        for group, viz in self.series.groups_visibility.items():
            try:
                menu_attr = getattr(self, f"{group}_viz_act")
                menu_attr.setChecked(viz)
            except AttributeError:
                pass

        ## Undo/redo
        can_undo_3D, can_undo_2D, _ = self.field.series_states.canUndo(self.field.section.n)
        self.undo_act.setEnabled(can_undo_3D or can_undo_2D)
        can_redo_3D, can_redo_2D, _ = self.field.series_states.canUndo(self.field.section.n, redo=True)
        self.redo_act.setEnabled(can_redo_3D or can_redo_2D)

        ## Check clipboard for paste options
        if self.field.clipboard:
            self.paste_act.setEnabled(True)
        else:
            self.paste_act.setEnabled(False)
            self.pasteattributes_act.setEnabled(False)

        ## Zarr images
        self.zarrimage_act.setEnabled(not self.field.section_layer.is_zarr_file)
        self.scalezarr_act.setEnabled(self.field.section_layer.is_zarr_file)

        ## Calibrate
        self.calibrate_act.setEnabled(bool(self.field.section.selected_traces))

    def changeMouseMode(self, new_mode):
        """Change the mouse mode of the field (pointer, panzoom, tracing...).

        Called when user clicks on mouse mode palette.

            Params:
                new_mode: the new mouse mode to set
        """
        self.field.setMouseMode(new_mode)
    
    def changeTraceMode(self):
        """Change the trace mode and shape."""

        current_shape = self.field.closed_trace_shape
        current_mode = self.series.getOption("trace_mode")

        structure = [
            ["Mode:"],
            [("radio",
                ("Scribble", current_mode == "scribble"),
                ("Poly", current_mode == "poly"),
                ("Combo", current_mode == "combo")
            )],
            ["Closed Trace Shape:"],
            [("radio",
                ("Trace", current_shape == "trace"),
                ("Rectangle", current_shape == "rect"),
                ("Ellipse", current_shape == "circle")
            )],
            [("check", ("Automatically merge selected traces", self.series.getOption("auto_merge")))],
            [("check", ("Apply rolling average while scribbling", self.series.getOption("roll_average"))),
             ("int", self.series.getOption("roll_window"))]
        ]

        response, confirmed = QuickDialog.get(self, structure, "Closed Trace Mode")

        if not confirmed:
            return
        
        if response[0][0][1]:
            new_mode = "scribble"

        elif response[0][1][1]:
            new_mode = "poly"

        else:
            new_mode = "combo"
        
        if response[1][1][1]:
            new_shape = "rect"

        elif response[1][2][1]:
            new_shape = "circle"

        else:
            new_shape = "trace"
        
        self.series.setOption("trace_mode", new_mode)
        self.field.closed_trace_shape = new_shape
        
        self.series.setOption("auto_merge", response[2][0][1])
        self.series.setOption("roll_average", response[3][0][1])
        self.series.setOption("roll_window", response[4])

    def changeTracingTrace(self, trace):
        """Change trace utilized by the user.

        Called when user clicks on trace palette.

            Params:
                trace: the new tracing trace to set
        """
        self.field.setTracingTrace(trace)
    
    def wheelEvent(self, event):
        """Called when mouse scroll is used."""
        # do nothing if middle button is clicked
        if self.field.mclick:
            return
        
        modifiers = QApplication.keyboardModifiers()

        # if zooming
        if modifiers == Qt.ControlModifier:
            self.activateWindow()
            field_cursor = self.field.cursor()
            p = self.field.mapFromGlobal(field_cursor.pos())
            x, y = p.x(), p.y()
            if not self.is_zooming:
                # check if user just started zooming in
                self.field.panzoomPress(x, y)
                self.zoom_factor = 1
                self.is_zooming = True

            if event.angleDelta().y() > 0:  # if scroll up
                self.zoom_factor *= 1.1
            elif event.angleDelta().y() < 0:  # if scroll down
                self.zoom_factor *= 0.9
            self.field.panzoomMove(zoom_factor=self.zoom_factor)
        
        # if changing sections
        elif modifiers == Qt.NoModifier:
            # check for the position of the mouse
            mouse_pos = event.point(0).pos()
            field_geom = self.field.geometry()
            if not field_geom.contains(mouse_pos.x(), mouse_pos.y()):
                return
            # change the section
            if event.angleDelta().y() > 0:  # if scroll up
                self.incrementSection()
            elif event.angleDelta().y() < 0:  # if scroll down
                self.incrementSection(down=True)
    
    def keyReleaseEvent(self, event):
        """Overwritten: checks for Ctrl+Zoom."""
        if self.is_zooming and event.key() == 16777249:
            self.field.panzoomRelease(zoom_factor=self.zoom_factor)
            self.is_zooming = False
        
        super().keyReleaseEvent(event)
        
    def modifyPointer(self, event=None):
        """Modify the pointer properties."""
        s, t = tuple(self.series.getOption("pointer"))
        structure = [
            ["Shape:"],
            [("radio", ("Rectangle", s=="rect"), ("Lasso", s=="lasso"))],
            ["Select:"],
            [("radio", ("All touched traces", t=="inc"), ("Only completed encircled traces", t=="exc"))],
            [("check", ("Display closest field item", self.series.getOption("display_closest")))]
        ]
        response, confirmed = QuickDialog.get(self, structure, "Pointer Settings")
        if not confirmed:
            return
        
        s = "rect" if response[0][0][1] else "lasso"
        t = "inc" if response[1][0][1] else "exc"
        self.series.setOption("pointer", [s, t])
        self.series.setOption("display_closest", response[2][0][1])
        self.seriesModified()
    
    def modifyGrid(self, event=None):
        """Modify the grid properties."""
        response, confirmed = GridDialog(
            self,
            tuple(self.series.getOption("grid")),
            self.series.getOption("sampling_frame_grid")
        ).exec()
        if not confirmed:
            return
        
        grid_response, sf_grid = response
        self.series.setOption("grid", grid_response)
        self.series.setOption("sampling_frame_grid", sf_grid)
        self.seriesModified()
    
    def modifyKnife(self, event=None):
        """Modify the knife properties."""
        structure = [
            [
                "Delete traces smaller than this percent:\n"
            ],
            [
                "% original trace:",
                ("float", self.series.getOption("knife_del_threshold"), (0, 100))
            ],
            [
                "\nOptionally smooth while cutting:"
            ],
            [
                ("check", ("Smooth cuts", self.series.getOption("roll_knife_average"))),
                ("int", self.series.getOption("roll_knife_window"))
            ]
        ]
        response, confirmed = QuickDialog.get(self, structure, "Knife")
        if not confirmed:
            return

        self.series.setOption("knife_del_threshold", response[0])
        self.series.setOption("roll_knife_average", response[1][0][1])
        self.series.setOption("roll_knife_window", response[2])
        
        self.seriesModified()
    
    def backspace(self):
        """Called when backspace is pressed."""
        # use table if focused; otherwise, use field
        w = self.getFocusWidget()
        if w: w.backspace()
    
    def copy(self):
        """Called when Ctrl+C is pressed."""
        w = self.getFocusWidget()
        if w: w.copy()
    
    def undo(self, redo=False):
        """Perform an undo/redo action.
        
            Params:
                redo (bool): True if redo should be performed
        """
        self.saveAllData()
        can_3D, can_2D, linked = self.field.series_states.canUndo(redo=redo)
        def act2D():
            self.field.undoState(redo)
        def act3D():
            self.field.series_states.undoState(redo)
            self.field.reload()
            self.field.table_manager.recreateTables()

        # both 3D and 2D possible and they are linked
        if can_3D and can_2D and linked:
            mbox = QMessageBox(self)
            mbox.setWindowTitle("Redo" if redo else "Undo")
            mbox.setText("This action is linked to multiple sections.\nPlease select how you would like to proceed.")
            mbox.setStandardButtons(QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
            mbox.setButtonText(QMessageBox.Yes, "All sections")
            mbox.setButtonText(QMessageBox.No, "Only this section")
            mbox.setButtonText(QMessageBox.Cancel, "Cancel")
            response = mbox.exec()
            if response == QMessageBox.Yes:
                act3D()
            elif response == QMessageBox.No:
                act2D()
        # both 3D and 2D possible but they are not linked
        elif can_3D and can_2D and not linked:
            favor_3D = self.field.series_states.favor3D(redo=redo)
            if favor_3D:
                act3D()
            else:
                act2D()
        # only 3D possible
        elif can_3D:
            act3D()
        # only 2D possible
        elif can_2D:
            act2D()
        
    def getFocusWidget(self):
        """Get the widget the user is focused on.
        
        Currently will only return a DataTable or the FieldWidget.
        """
        table = self.field.table_manager.hasFocus()
        if table:
            return table
        else:
            return self.field

