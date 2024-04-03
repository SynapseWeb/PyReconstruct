import math

from PySide6.QtGui import QPainter

from .section_layer import SectionLayer
from .zarr_layer import ZarrLayer

from PyReconstruct.modules.datatypes import (
    Series,
    Transform,
    Trace,
    Flag
)
from PyReconstruct.modules.backend.func import SectionStates, SeriesStates
from PyReconstruct.modules.calc import (
    centroid,
    lineDistance,
    pixmapPointToField
)
from PyReconstruct.modules.gui.utils import notify, notifyConfirm

class FieldView():

    def createFieldView(self, series : Series):
        """Create the field view object.
        
            Params:
                series (Series): the series object
        """
        # get series and current section
        self.series = series
        self.section = self.series.loadSection(self.series.current_section)
        # load the section states
        self.clearStates()
        # initialize the current section
        self.series_states[self.section]

        # get image dir
        if self.series.src_dir == "":
            self.src_dir = self.series.getwdir()
        else:
            self.src_dir = self.series.src_dir

        # create section view
        self.section_layer = SectionLayer(self.section, self.series)

        # create zarr view if applicable
        self.createZarrLayer()
        
        # b section and view placeholder
        self.b_section = None
        self.b_section_layer = None

        # placeholders for the table manager
        self.obj_table_manager = None
        self.ztrace_table_manager = None
        self.trace_table_manager = None
        self.section_table_manager = None
        self.flag_table_manager = None

        # hide/show defaults
        self.hide_trace_layer = False
        self.show_all_traces = False
        self.hide_image = False

        # propagate tform defaults
        self.propagate_tform = False
        self.stored_tform = Transform([1,0,0,0,1,0])
        self.propagated_sections = set()

        # copy/paste clipboard
        self.clipboard = []
    
    def reload(self, clear_states=False):
        """Reload the section data (used if section files were modified, usually through object list)."""
        # reload the actual sections
        self.section = self.series.loadSection(self.series.current_section)
        self.section_layer.section = self.section
        if self.b_section:
            self.b_section = self.series.loadSection(self.b_section.n)
            self.b_section_layer.section = self.b_section
        # clear all the section states
        if clear_states:
            self.clearStates()
        # clear the selected traces
        self.section.selected_traces = []
        if self.b_section:
            self.b_section.selected_traces = []
        # update the palette
        self.mainwindow.mouse_palette.updateBC()
        
        self.generateView()

        # notify that the series has been modified
        self.mainwindow.seriesModified(True)
    
    def createZarrLayer(self):
        """Create a zarr layer."""
        if self.series.zarr_overlay_fp and self.series.zarr_overlay_group:
            self.zarr_layer = ZarrLayer(self.series)
        else:
            self.zarr_layer = None

    def reloadImage(self):
        """Reload the section images (used if transform or image source is modified)."""
        self.section_layer.loadImage()
        if self.b_section is not None:
            self.b_section_layer.loadImage()
        self.generateView()
    
    def updateData(self, clear_tracking=True):
        """Update the series data object and the tables."""
        # update the series data tracker
        self.series.data.updateSection(
            self.section, 
            update_traces=True,
            all_traces=False
        )

        # update the object table
        if self.obj_table_manager:
            self.obj_table_manager.updateSection(
                self.section
            )
        
        # update the trace table
        if self.trace_table_manager:
            self.trace_table_manager.update()
        
        # update the ztrace table
        if self.ztrace_table_manager:
            self.ztrace_table_manager.update()
        
        # update the section table
        if self.section_table_manager:
            self.section_table_manager.updateSection(self.section.n)

        # update the flag table
        if self.flag_table_manager:
            self.flag_table_manager.updateSection(self.section)
        
        if clear_tracking:
            self.section.clearTracking()
            self.series.modified_ztraces = set()
    
    def clearStates(self):
        """Create/clear the states for each section."""
        self.series_states = SeriesStates(self.series)

    def saveState(self):
        """Save the current traces and transform.
        
        ALSO updates the lists.
        """
        # save the current state
        section_states = self.series_states[self.series.current_section]
        section_states.addState(self.section, self.series)

        # update the data/tables
        self.updateData()

        # check if a series undo/redo has been overwritten
        self.series_states.checkOverwrite(self.section.n)

        # notify that the series has been edited
        self.mainwindow.seriesModified(True)
        self.mainwindow.checkActions()

    def undoState(self, redo=False):
        """Undo last action (switch to last state)."""
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return

        # end any pending events
        self.endPendingEvents()  # function extended in inherited class
        
        # clear selected straces
        self.section.selected_traces = []
        self.section.selected_ztraces = []

        # get the last undo state
        self.series_states.undoSection(self.section, redo)

        # update the data/tables
        self.updateData()
        
        self.generateView()
    
    def seriesUndo(self, redo=False):
        """Undo an action across the series.
        
            Params:
                redo (bool): True if should redo instead of undo
        """
        self.series_states.undoState(redo)
        self.reload()
        self.refreshTables()
    
    def setPropagationMode(self, propagate : bool):
        """Set the propagation mode.
        
            Params:
                propagate (bool): whether to begin or finish propagating
        """
        self.propagate_tform = propagate
        if self.propagate_tform:
            self.stored_tform = Transform([1,0,0,0,1,0])
            self.propagated_sections = set([self.series.current_section])
        self.update()
        
    def propagateTo(self, to_end : bool = True, log_event=True):
        """Propagate the stored transform to the start/end of series.
        
            Params:
                to_end (bool): True propagates to the end, False propagates to beginning
        """
        # save the current section
        self.section.save()
        
        included_sections = []
        for snum in self.series.sections:
            if snum not in self.propagated_sections:
                modify_section = (
                    (to_end and snum > self.series.current_section)
                    or
                    (not to_end and snum < self.series.current_section)
                )
                if modify_section: included_sections.append(snum)
        
        for snum in included_sections:
            section = self.series.loadSection(snum)
            if section.align_locked:
                if not notifyConfirm("Locked sections will not be modified.\nWould you still like to propagate the transform?"):
                    return
                break
        
        for snum in included_sections:
            section = self.series.loadSection(snum)
            new_tform = self.stored_tform * section.tform
            section.tform = new_tform
            section.save()
            self.propagated_sections.add(snum)
            if log_event:
                self.series.addLog(None, snum, "Modify transform")
        
        self.reload()
    
    def swapABsections(self):
        """Switch the A and B sections."""
        self.section, self.b_section = self.b_section, self.section
        self.section_layer, self.b_section_layer = self.b_section_layer, self.section_layer
        if self.section is not None:
            self.series.current_section = self.section.n
    
    def changeSection(self, new_section_num : int):
        """Change the displayed section.
        
            Params:
                new_section_num (int): the new section number to display
        """
        # check if requested section exists
        if new_section_num not in self.series.sections:
            return
        
        # check if already on section
        if new_section_num == self.series.current_section:
            return
        
        # move current section data to b section
        self.swapABsections()

        # load new section if required
        if new_section_num != self.series.current_section:
            # load section
            self.section = self.series.loadSection(new_section_num)
            # load section view
            self.section_layer = SectionLayer(self.section, self.series)
            # set new current section
            self.series.current_section = new_section_num
            # clear selected traces
            self.section.selected_traces = []
        
        # create section undo/redo state object if needed
        states = self.series_states[new_section_num]
        if not states.initialized:
            states.initialize(self.section, self.series)
        
        # reload trace list
        if self.trace_table_manager:
            self.trace_table_manager.loadSection(self.section)
        
        # propagate transform if requested
        if (self.propagate_tform and
            not self.section.align_locked and
            new_section_num not in self.propagated_sections):
            current_tform = self.section.tform
            new_tform = self.stored_tform * current_tform
            self.section_layer.changeTform(new_tform)
            self.propagated_sections.add(new_section_num)

        # generate view and update status bar
        self.generateView()
    
    def findTrace(self, trace_name : str, index=0):
        """Focus the window view on a given trace.
        
            Params:
                trace_name (str): the name of the trace to focus on
                index (int): find the nth trace on the section
        """
        # check if the trace exists
        if trace_name not in self.section.contours or self.section.contours[trace_name].isEmpty():
            return
        try:
            trace = self.section.contours[trace_name][index]
        except IndexError:
            return
        
        # set the window to frame the object
        tform = self.section.tform
        min_x, min_y, max_x, max_y = trace.getBounds(tform)
        range_x = max_x - min_x
        range_y = max_y - min_y
        self.series.window = [min_x - range_x/2, min_y - range_y/2, range_x * 2, range_y * 2]

        # set the trace as the only selected trace
        if trace.hidden or self.hide_trace_layer or self.series.getAttr(trace.name, "locked"):
            self.section.selected_traces = []
        else:
            self.section.selected_traces = [trace]

        self.generateView()
    
    def findContour(self, contour_name : str):
        """Focus the window view on a given trace.
        
            Params:
                contour_name (str): the name of the contour to focus on
        """
        # check if contour exists
        if contour_name not in self.section.contours or self.section.contours[contour_name].isEmpty():
            return
        
        # # get the minimum window requirements (1:1 screen to image pixels)
        # min_window_w = self.section.mag * self.section_layer.pixmap_dim[0]
        # min_window_h = self.section.mag * self.section_layer.pixmap_dim[1]
        
        # get the bounds of the contour and set the window
        contour = self.section.contours[contour_name]
        tform = self.section.tform
        vals = [trace.getBounds(tform) for trace in contour]
        
        min_x = min([v[0] for v in vals])
        min_y = min([v[1] for v in vals])
        max_x = max([v[2] for v in vals])
        max_y = max([v[3] for v in vals])
        
        range_x = max_x - min_x
        range_y = max_y - min_y

        # Get values of image (if exists) in order to figure out what 100% zoom means

        if self.section_layer.image_found:

            # This should probably be a stand alone function
            # It is used vertbatim in home method below
        
            tform = self.section.tform
            xvals = []
            yvals = []
        
            # get the field location of the image
            for p in self.section_layer.base_corners:
            
                x, y = [n * self.section.mag for n in p]
                x, y = tform.map(x, y)
                xvals.append(x)
                yvals.append(y)

            max_img_dist = max(xvals + yvals)

        else: # default to some arbitrary large size

            max_img_dist = 50

        zoom = self.series.getOption("find_zoom")

        new_range_x = range_x + ((100 - zoom)/100 * (max_img_dist - range_x))
        new_range_y = range_y + ((100 - zoom)/100 * (max_img_dist - range_y))

        new_x = min_x - ( (new_range_x - range_x) / 2 )
        new_y = min_y - ( (new_range_y - range_y) / 2 )

        # # check if minimum requirements are met
        # if new_range_x < min_window_w:
        #     new_x -= (min_window_w - new_range_x) / 2
        #     new_range_x = min_window_w
        # elif new_range_y < min_window_h:
        #     new_y -= (min_window_h - new_range_y) / 2
        #     new_range_y = min_window_h
        
        self.series.window = [
            
            new_x,
            new_y,
            new_range_x,
            new_range_y
            
        ]

        # set the selected traces
        self.section.selected_traces = []
        for trace in contour.getTraces():
            if not trace.hidden and not self.hide_trace_layer:
                self.section.addSelectedTrace(trace)

        self.generateView()
    
    def findFlag(self, flag : Flag):
        """Find a flag on the current section"""
        # check if flag exists
        found = False
        for f in self.section.flags:
            if flag.equals(f):
                flag = f
                found = True
        if not found:
            return
        
        # # get the minimum window requirements (1:1 screen to image pixels)
        # min_window_w = self.section.mag * self.section_layer.pixmap_dim[0]
        # min_window_h = self.section.mag * self.section_layer.pixmap_dim[1]
        
        # get the bounds of the contour and set the window
        tform = self.section.tform
        x, y = tform.map(flag.x, flag.y)
        
        min_x = max_x = x
        min_y = max_y = y
        
        range_x = max_x - min_x
        range_y = max_y - min_y

        # Get values of image (if exists) in order to figure out what 100% zoom means

        if self.section_layer.image_found:

            # This should probably be a stand alone function
            # It is used vertbatim in home method below
        
            tform = self.section.tform
            xvals = []
            yvals = []
        
            # get the field location of the image
            for p in self.section_layer.base_corners:
            
                x, y = [n * self.section.mag for n in p]
                x, y = tform.map(x, y)
                xvals.append(x)
                yvals.append(y)

            max_img_dist = max(xvals + yvals)

        else: # default to some arbitrary large size

            max_img_dist = 50

        zoom = self.series.getOption("find_zoom")

        # modifier for flags: cap at 99% zoom
        if zoom > 99:
            zoom = 99

        new_range_x = range_x + ((100 - zoom)/100 * (max_img_dist - range_x))
        new_range_y = range_y + ((100 - zoom)/100 * (max_img_dist - range_y))

        new_x = min_x - ( (new_range_x - range_x) / 2 )
        new_y = min_y - ( (new_range_y - range_y) / 2 )

        # # check if minimum requirements are met
        # if new_range_x < min_window_w:
        #     new_x -= (min_window_w - new_range_x) / 2
        #     new_range_x = min_window_w
        # elif new_range_y < min_window_h:
        #     new_y -= (min_window_h - new_range_y) / 2
        #     new_range_y = min_window_h
        
        self.series.window = [
            
            new_x,
            new_y,
            new_range_x,
            new_range_y
            
        ]

        # if the flag is an import conflict, hide everything except the conflict traces
        if flag.name.startswith("import-conflict_"):
            flag_cname = flag.name[flag.name.find("_")+1:]
            for cname, contour in self.section.contours.items():
                if cname == flag_cname:
                    for trace in contour:
                        trace.hidden = False
                else:
                    for trace in contour:
                        trace.hidden = True

        # set the selected flags
        show_flags = self.series.getOption("show_flags")
        if (show_flags == "all" or
            (show_flags == "unresolved" and not flag.resolved)):
            self.section.selected_flags = [flag]

        self.generateView()
    
    def home(self):
        """Set the view to the image."""
        # check is an image has been loaded
        if not self.section_layer.image_found:
            return
        
        tform = self.section.tform
        xvals = []
        yvals = []
        # get the field location of the image
        for p in self.section_layer.base_corners:
            x, y = [n*self.section.mag for n in p]
            x, y = tform.map(x, y)
            xvals.append(x)
            yvals.append(y)
        self.series.window = [
            min(xvals),
            min(yvals),
            max(xvals) - min(xvals),
            max(yvals) - min(yvals)
        ]
        self.generateView()
    
    def moveTo(self, snum : int, x : float, y : float):
        """Move to a specified section number and coordinates (used from 3D scene).
        
            Params:
                snum (int): the section number to move to
                x (int): the x coordinate to focus on
                y (int): the y coordinate to focus on
        """
        # check for section number
        if snum not in self.series.sections:
            return

        if self.series.current_section != snum:
            self.changeSection(snum)
        
        # set one micron diameter around object
        self.series.window = [x-0.5, y-0.5, 1, 1]

        self.generateView()
    
    def selectTrace(self, trace : Trace):
        """Select/deselect a single trace.
        
            Params:
                trace (Trace): the trace to select
        """
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return
        
        if not trace:
            return
        if trace in self.section.selected_traces:
            self.section.selected_traces.remove(trace)
        else:
            self.section.addSelectedTrace(trace)

        self.generateView(generate_image=False)
    
    def selectZtrace(self, ztrace_i : tuple):
        """Select/deselect a single ztrace point.
        
            Params:
                ztrace_i (tuple): the ztrace, index of point selected
        """
        # disbale if trace layer is hidden
        if self.hide_trace_layer:
            return
        
        # check if ztrace point has been selected
        if ztrace_i in self.section.selected_ztraces:
            self.section.selected_ztraces.remove(ztrace_i)
        else:
            self.section.selected_ztraces.append(ztrace_i)
        
        self.generateView(generate_image=False)

    def selectFlag(self, flag : Flag):
        """Select/deselect a single flag.
        
            Params:
                flag (Flag): the flag to select
        """
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return
        
        # check if flag has been selected
        if flag in self.section.selected_flags:
            self.section.selected_flags.remove(flag)
        else:
            self.section.selected_flags.append(flag)
        
        self.generateView(generate_image=False)
    
    def selectTraces(self, traces : list[Trace], ztraces_i : list):
        """Select/deselect a set of traces.
        
            Params:
                traces (list[Trace]): the traces to select
        """
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return

        for trace in traces:
            if trace not in self.section.selected_traces:
                self.section.addSelectedTrace(trace)
        for ztrace_i in ztraces_i:
            if ztrace_i not in self.section.selected_ztraces:
                self.section.selected_ztraces.append(ztrace_i)
            
        self.generateView(generate_image=False)
    
    def changeAlignment(self, new_alignment : str, refresh_data=True):
        """Change the alignment setting for the series.
        
            Params:
                new_alignment (str): the name of the new alignment
        """
        self.series.alignment = new_alignment

        # turn off propagation
        self.setPropagationMode(False)
        
        self.reload()

        # refresh data and tables
        self.refreshTables(refresh_data)
    
    def changeBCProfile(self, new_profile):
        """Change the brightness/contrast profile for the series.
        
            Params:
                new_profile (str): the name of the profile to switch to
        """
        self.series.bc_profile = new_profile

        # update palette and tables
        self.mainwindow.mouse_palette.updateBC()
        if self.section_table_manager:
            self.section_table_manager.updateSections(self.series.sections.keys())

        self.generateView()
    
    def translateTform(self, dx : float, dy : float):
        """Translate the transform for the entire section.
            Params:
                dx (float): x-translate
                dy (float): y-translate
        """
        new_tform = self.section.tform.getList()
        new_tform[2] += dx
        new_tform[5] += dy
        new_tform = Transform(new_tform)
        self.changeTform(new_tform)
    
    def rotateTform(self, cc=True):
        """Rotate the section transform."""
        tform = self.section.tform
        tform_list = tform.getList()
        x, y = pixmapPointToField(
            self.mouse_x,
            self.mouse_y,
            self.pixmap_dim,
            self.series.window,
            self.section.mag
        )
        translate_tform = Transform([1, 0, x, 0, 1, y])
        t = math.pi / 720
        t *= 1 if cc else -1
        sin = math.sin(t)
        cos = math.cos(t)
        rotate_tform = Transform([
            cos, -sin, 0,
            sin, cos, 0
        ])
        new_tform = (
            (tform * translate_tform.inverted() * rotate_tform * translate_tform)
        )
        self.changeTform(new_tform)
    
    def translate(self, dx : float, dy : float):
        """Translate the transform OR the selected traces.
        
            Params:
                dx (float): x-translate
                dy (float): y-translate
        """
        if self.section.selected_traces or self.section.selected_ztraces:
            self.section.translateTraces(dx, dy)
            self.saveState()
            self.generateView()
        else:
            self.translateTform(dx, dy)
    
    def resizeWindow(self, pixmap_dim : tuple):
        """Convert the window to match the proportions of the pixmap.
        
            Params:
                pixmap_dim (tuple): the w and h of the pixmap view
        """
        # get dimensions of field window and pixmap
        window_x, window_y, window_w, window_h = tuple(self.series.window)
        if window_w == 0: window_w = 1e-3
        if window_h == 0: window_h = 1e-3  # prevent dividing by zero
        pixmap_w, pixmap_h = tuple(pixmap_dim)
        window_ratio = window_w/window_h
        pixmap_ratio = pixmap_w / pixmap_h

        # resize window to match proportions of current geometry
        if abs(window_ratio - pixmap_ratio) > 1e-6:
            # increase the width
            if window_ratio < pixmap_ratio: 
                new_w = window_h * pixmap_ratio
                new_x = window_x - (new_w - window_w) / 2
                window_w = new_w
                window_x = new_x
            # increase the height
            else:
                new_h = window_w / pixmap_ratio
                new_y = window_y - (new_h - window_h) / 2
                window_h = new_h
                window_y = new_y
            self.series.window = [window_x, window_y, window_w, window_h]
    
    def setView(self, mag : float):
        """Set the scaling value for the view.
        
            Params:
                scaling (float): the new scaling value
        """
        # calculate the scaling factor for the magnification
        factor = mag * self.series.screen_mag

        # reset the window
        w, h = self.series.window[2], self.series.window[3]
        new_w, new_h = w / factor, h / factor
        self.series.window[0] += (w - new_w) / 2
        self.series.window[1] += (h - new_h) / 2
        self.series.window[2] = new_w
        self.series.window[3] = new_h

        self.generateView()
    
    def toggleHideAllTraces(self):
        """Hide the trace layer."""
        self.hide_trace_layer = not self.hide_trace_layer
        if self.hide_trace_layer:
            self.show_all_traces = False
            # remove hidden traces that were selected
            for trace in self.section.selected_traces:
                if trace.hidden:
                    self.section.selected_traces.remove(trace)
        self.generateView()
    
    def toggleShowAllTraces(self):
        """Toggle show all traces regardless of hiding status."""
        self.show_all_traces = not self.show_all_traces
        if self.show_all_traces:
            self.hide_trace_layer = False
        # remove hidden traces that were selected
        else:
            for trace in self.section.selected_traces:
                if trace.hidden:
                    self.section.selected_traces.remove(trace)
        self.generateView()
    
    def toggleHideImage(self):
        """Toggle hide the image from view."""
        self.hide_image = not self.hide_image
        self.generateView(generate_traces=False)
    
    def affineAlign(self):
        """Modify the linear transformation using points from the selected trace.
        """
        if not self.b_section or self.section.align_locked:
            return
        
        # gather traces
        a_traces = self.section.selected_traces.copy()
        b_traces = self.b_section.selected_traces.copy()

        # check number of selected traces
        alen = len(a_traces)
        blen = len(b_traces)
        if alen < 3:
            notify("Please select 3 or more traces for aligning.")
        if alen != blen:
            notify("Please select the same number of traces on each section.")
            return
        contour_name = a_traces[0].name

        # check that all traces have same name
        for trace in (a_traces + b_traces):
            if trace.name != contour_name:
                notify("Please select traces of the same name on both sections.")
                return

        # gather points from each section
        centsA = []
        for trace in a_traces:
            centsA.append(centroid(trace.points))
        centsB = []
        tformB = self.b_section.tform
        for trace in b_traces:
            pts = tformB.map(trace.points)
            centsB.append(centroid(pts))
        
        # calculate the tform
        a2b_tform = Transform.estimateTform(centsA, centsB)

        # change the transform
        self.changeTform(a2b_tform)
    
    def calibrateMag(self, trace_lengths : dict, log_event=True):
        """Calibrate the pixel mag based on the lengths of given traces.

            Params:
                trace_lengths (dict): the lengths of the selected traces (name: length)
        """
        # get an average scaling factor across the selected traces
        sum_scaling = 0
        total = 0
        for cname in trace_lengths:
            for trace in self.section.contours[cname]:
                # get the length of the trace with the given transform
                tform = self.section.tform
                d = lineDistance(tform.map(trace.points), closed=False)
                # scaling = expected / actual
                sum_scaling += trace_lengths[trace.name] / d
                total += 1
        
        # calculate new mag
        avg_scaling = sum_scaling / total
        new_mag = self.section.mag * avg_scaling

        self.setMag(new_mag, log_event)
    
    def setMag(self, new_mag : float, log_event=True):
        """Set a new magnification for the series.
        
            Params:
                new_mag (float): the new magnification for the series
        """

        # apply new mag to every section
        for snum, section in self.series.enumerateSections(
            message="Changing series magnification..."
        ):
            section.setMag(new_mag)
            section.save()
        
        if log_event:
            self.series.addLog(None, None, "Calibrate series")
        
        # reload the field
        self.reload()
        self.refreshTables(refresh_data=True)

    def generateView(self, pixmap_dim : tuple, generate_image=True, generate_traces=True, blend=False):
        """Generate the view seen by the user in the main window.
        
            Params:
                pixmap_dim (tuple): the w and h of the pixmap view
                generate_image (bool): whether or not to redraw the image
                generate_traces (bool): whether or not to redraw the traces
        """
        # resize series window to match view proportions
        self.resizeWindow(pixmap_dim)

        # calculate the scaling
        window_x, window_y, window_w, window_h = tuple(self.series.window)
        pixmap_w, pixmap_h = tuple(pixmap_dim)
        # scaling: ratio of screen pixels to actual image pixels (should be equal)
        x_scaling = pixmap_w / (window_w / self.section.mag)
        y_scaling = pixmap_h / (window_h / self.section.mag)
        assert(abs(x_scaling - y_scaling) < 1e-6)
        self.scaling = x_scaling

        # generate section view
        view = self.section_layer.generateView(
            pixmap_dim,
            self.series.window,
            generate_image=generate_image,
            generate_traces=generate_traces,
            hide_traces=self.hide_trace_layer,
            show_all_traces=self.show_all_traces,
            hide_image=self.hide_image
        )

        # blend b section if requested
        if blend and self.b_section is not None:
            # generate b section view
            b_view = self.b_section_layer.generateView(
                pixmap_dim,
                self.series.window,
                generate_image=generate_image,
                generate_traces=generate_traces,
                hide_traces=self.hide_trace_layer,
                show_all_traces=self.show_all_traces,
                hide_image=self.hide_image
            )
            # overlay a and b sections
            painter = QPainter(view)
            painter.setOpacity(0.5)
            painter.drawPixmap(0, 0, b_view)
            painter.end()
        
        # overlay zarr if requested
        if self.zarr_layer:
            zarr_layer = self.zarr_layer.generateZarrLayer(
                self.section,
                pixmap_dim,
                self.series.window
            )
            if zarr_layer:
                painter = QPainter(view)
                if not self.hide_image:
                    painter.setOpacity(0.3)
                painter.drawPixmap(0, 0, zarr_layer)
                painter.end()
        
        return view
    
    def quickAlign(self):
        """Do a quick translational alignment of the current secion and b section."""  
        if not self.b_section_layer or self.section.align_locked:
            return

        from skimage import registration
        
        pixmap_dim = self.section_layer.pixmap_dim
        window = self.series.window
        
        arr1 = self.b_section_layer.generateImageArray(pixmap_dim, window)
        arr2 = self.section_layer.generateImageArray(pixmap_dim, window)

        # Perform phase correlation to find translation
        model = registration.phase_cross_correlation(arr1, arr2)
        error = model[1]
        shift_x = model[0][1] / self.scaling * self.section.mag
        shift_y = model[0][0] / self.scaling * self.section.mag

        current_tform = self.section.tform
        shift_tform = Transform([
            1,
            0,
            shift_x, 
            0,
            1,
            shift_y
        ])
        self.section.tform = shift_tform * current_tform

        self.generateView()
        self.saveState()
    
    def lockObjects(self, names=None):
        """Lock a set of objects.
        
            Params:
                names (set): the set of names to lock
        """
        if names is None:
            names = set([t.name for t in self.section.selected_traces])
        
        self.series_states.addState()

        for name in names:
            self.series.setAttr(name, "locked", True)
        if self.obj_table_manager:
            self.obj_table_manager.updateObjects(names)
        self.deselectAllTraces()
    
    def unlockObject(self, name=None):
        """Unlock a single object.
        
            Params:
                name (str): the name of the object to unlock
        """
        if name is None:
            name = self.clicked_trace.name
        
        self.series_states.addState()

        self.series.setAttr(name, "locked", False)
        if self.obj_table_manager:
            self.obj_table_manager.updateObjects([name])
    
    # CONNECT SECTIONVIEW FUNCTIONS TO FIELDVIEW CLASS

    def deleteTraces(self, traces=None):
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return
        modified = self.section.deleteTraces(traces)
        if modified:
            self.generateView(generate_image=False)
            self.saveState()
    
    def mergeSelectedTraces(self, traces : list = None, merge_attrs=False):
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return
        if self.section.selected_traces:
            self.section_layer.mergeSelectedTraces(traces, merge_attrs)
            self.generateView(generate_image=False)
            self.saveState()
    
    def cutTrace(self, scalpel_trace):
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return
        elif len(self.section.selected_traces) == 0:
            notify("Please select the trace you wish to cut.")
            return
        elif len(self.section.selected_traces) > 1:
            notify("Please select only one trace to cut at a time.")
            return
        self.section_layer.cutTrace(scalpel_trace)
        self.generateView(generate_image=False)
        self.saveState()
    
    def newTrace(self, pix_trace, tracing_trace, closed=True, log_event=True):
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            self.generateView(generate_image=False)
            return
        self.section_layer.newTrace(pix_trace, tracing_trace, closed=closed, log_event=log_event)
        self.generateView(generate_image=False)
        self.mainwindow.mouse_palette.incrementButton()  # increment the mouse palette if necessary
        self.saveState()
    
    def placeStamp(self, pix_x, pix_y, stamp):
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return
        self.section_layer.placeStamp(pix_x, pix_y, stamp)
        self.generateView(generate_image=False)
        self.mainwindow.mouse_palette.incrementButton()  # increment the mouse palette if necessary
        self.saveState()
    
    def placeGrid(self, pix_x, pix_y, trace, w, h, dx, dy, nx, ny):
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return
        self.section_layer.placeGrid(
            pix_x, pix_y, trace, w, h, dx, dy, nx, ny
        )
        self.generateView(generate_image=False)
        self.mainwindow.mouse_palette.incrementButton()  # increment the mouse palette if necessary
        self.saveState()
    
    def placeFlag(self, title, pix_x, pix_y, color, comment):
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return
        self.section_layer.placeFlag(
            title, pix_x, pix_y, color, comment
        )
        self.generateView(generate_image=False)
        self.saveState()
    
    def deselectAllTraces(self):
        # disable if trace layer is hidden
        if self.zarr_layer:
            self.zarr_layer.deselectAll()
            self.generateView(generate_image=False)
        if not self.hide_trace_layer:
            self.section.deselectAllTraces()
            self.generateView(generate_image=False)
    
    def selectAllTraces(self):
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return
        self.section.selectAllTraces()
        self.generateView(generate_image=False)
    
    def hideTraces(self, traces=None, hide=True):
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return
        modified = self.section.hideTraces(traces, hide)
        if modified:
            self.generateView(generate_image=False)
            self.saveState()
    
    def unhideAllTraces(self):
        if self.hide_trace_layer:
            self.hide_trace_layer = False
        modified = self.section.unhideAllTraces()
        if modified:
            self.generateView()
            self.saveState()
    
    def makeNegative(self, negative=True):
        self.section.makeNegative(negative)
        self.saveState()
    
    def changeBrightness(self, change):
        self.section_layer.changeBrightness(change)
        self.series.data.updateSection(self.section)
        if self.section_table_manager:
            self.section_table_manager.updateSection(self.section.n)
        self.mainwindow.seriesModified(True)
        self.generateView(generate_traces=False)
    
    def changeContrast(self, change):
        self.section_layer.changeContrast(change)
        self.series.data.updateSection(self.section)
        if self.section_table_manager:
            self.section_table_manager.updateSection(self.section.n)
        self.mainwindow.seriesModified(True)
        self.generateView(generate_traces=False)
    
    def changeTform(self, new_tform):
        # check for section locked status
        if self.section.align_locked:
            return

        # check if propagating
        if self.propagate_tform:
            current_tform = self.section_layer.section.tform
            dtform = new_tform * current_tform.inverted()
            self.stored_tform = dtform * self.stored_tform

        self.section_layer.changeTform(new_tform)
        
        self.generateView()
        self.saveState()
    
    def copy(self):
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return
        copied_traces = self.section_layer.getCopiedTraces()
        if copied_traces:
            self.clipboard = copied_traces
    
    def cut(self):
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return
        copied_traces = self.section_layer.getCopiedTraces(cut=True)
        if copied_traces:
            self.clipboard = copied_traces
            self.generateView(generate_image=False)
            self.saveState()
    
    def paste(self):
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return
        self.section_layer.pasteTraces(self.clipboard)
        self.generateView(generate_image=False)
        self.saveState()
    
    def pasteAttributes(self):
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return
        self.section_layer.pasteAttributes(self.clipboard)
        self.generateView(generate_image=False)
        self.saveState()
    
    
