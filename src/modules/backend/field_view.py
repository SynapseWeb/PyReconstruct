from PySide6.QtGui import QPainter

from modules.pyrecon.series import Series
from modules.pyrecon.transform import Transform
from modules.pyrecon.trace import Trace

from modules.backend.section_layer import SectionLayer
from modules.backend.state_manager import SectionStates

from modules.calc.quantification import centroid, estimateLinearTform

class FieldView():

    def __init__(self, series : Series):
        """Create the field view object.
        
            Params:
                series (Series): the series object
        """
        # get series and current section
        self.series = series
        self.section = self.series.loadSection(self.series.current_section)
        # load the section state
        self.series_states = {}
        self.series_states[self.series.current_section] = SectionStates(self.section)

        # get image dir
        if self.series.src_dir == "":
            self.src_dir = self.series.getwdir()
        else:
            self.src_dir = self.series.src_dir

        # create section view
        self.section_layer = SectionLayer(self.section, self.series)

        # b section and view placeholder
        self.b_section_number = None
        self.b_section = None
        self.b_section_layer = None

        # placeholders for the table manager
        self.obj_table_manager = None
        self.ztrace_table_manager = None
        self.trace_table_manager = None
        self.section_table_manager = None

        # hide/show defaults
        self.hide_trace_layer = False
        self.show_all_traces = False

        # propogate tform defaults
        self.propogate_tform = False
        self.stored_tform = Transform([1,0,0,0,1,0])
        self.propogated_sections = []

        # copy/paste clipboard
        self.clipboard = []
    
    def reload(self):
        """Reload the section data (used if section files were modified, usually through object list)."""
        # reload the actual sections
        self.section = self.series.loadSection(self.series.current_section)
        self.section_layer.section = self.section
        if self.b_section:
            self.b_section = self.series.loadSection(self.b_section_number)
            self.b_section_layer.section = self.b_section
        # clear all the section states
        self.series_states = {}
        self.series_states[self.series.current_section] = SectionStates(self.section)
        if self.b_section:
            self.series_states[self.b_section] = SectionStates(self.b_section)
        # clear the selected traces
        self.section_layer.selected_traces = []
        if self.b_section:
            self.b_section_layer.selected_traces = []
        
        self.generateView()
        # notify that the series has been modified
        self.mainwindow.seriesModified(True)
    
    def reloadImage(self):
        """Reload the section images (used if transform or image source is modified)."""
        self.section_layer.loadImage()
        if self.b_section is not None:
            self.b_section_layer.loadImage()
        self.generateView()

    def saveState(self):
        """Save the current traces and transform.
        
        ALSO updates the lists.
        """
        # save the current state
        section_states = self.series_states[self.series.current_section]
        section_states.addState(self.section)

        # update the object table
        if self.obj_table_manager:
            self.obj_table_manager.updateSection(
                self.section,
                self.series.current_section
            )
        
        # update the trace table
        if self.trace_table_manager:
            self.trace_table_manager.update()
        
        # clear the tracked added/removed traces
        self.section.clearTracking()

        # notify that the series has been edited
        self.mainwindow.seriesModified(True)

    def undoState(self):
        """Undo last action (switch to last state)."""
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return
        
        # clear selected straces
        self.section_layer.selected_traces = []

        # get the last undo state
        section_states = self.series_states[self.series.current_section]
        modified_contours = section_states.undoState(self.section)
        if modified_contours is None:
            return
        
        # update the object table
        if self.obj_table_manager:
            for contour in modified_contours:
                self.obj_table_manager.updateContour(
                    contour,
                    self.section,
                    self.series.current_section
                )
            
        # update the trace table
        if self.trace_table_manager:
            self.trace_table_manager.loadSection()
        
        self.generateView()
    
    def redoState(self):
        """Redo an undo (switch to last undid state)."""
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return
        
        # clear the selected traces
        self.section_layer.selected_traces = []

        # get the last redo state
        section_states = self.series_states[self.series.current_section]
        modified_contours = section_states.redoState(self.section)
        if modified_contours is None:
            return
        
        # update the object table
        if self.obj_table_manager:
            for contour in modified_contours:
                self.obj_table_manager.updateContour(
                    contour,
                    self.section,
                    self.series.current_section
                )
            
        # update the trace table
        if self.trace_table_manager:
            self.trace_table_manager.loadSection()
        
        self.generateView()
    
    def setPropogationMode(self, propogate : bool):
        """Set the propogation mode.
        
            Params:
                propogate (bool): whether to begin or finish propogating
        """
        self.propogate_tform = propogate
        if self.propogate_tform:
            self.stored_tform = Transform([1,0,0,0,1,0])
            self.propogated_sections = [self.series.current_section]
        
    def propogateTo(self, to_end : bool = True):
        """Propogate the stored transform to the start/end of series.
        
            Params:
                to_end (bool): True propogates to the end, False propogates to beginning
        """
        # save the current section
        self.section.save()
        
        for snum in self.series.sections:
            modify_section = (
                (to_end and snum > self.series.current_section)
                or
                (not to_end and snum < self.series.current_section)
            )
            if modify_section:
                section = self.series.loadSection(snum)
                new_tform = self.stored_tform * section.tforms[self.series.alignment]
                section.tforms[self.series.alignment] = new_tform
                section.save()
                self.propogated_sections.append(snum)
        
        self.reload()
    
    def swapABsections(self):
        """Switch the A and B sections."""
        self.series.current_section, self.b_section_number = self.b_section_number, self.series.current_section
        self.section, self.b_section = self.b_section, self.section
        self.section_layer, self.b_section_layer = self.b_section_layer, self.section_layer
    
    def changeSection(self, new_section_num : int):
        """Change the displayed section.
        
            Params:
                new_section_num (int): the new section number to display
        """
        # check if requested section exists
        if new_section_num not in self.series.sections:
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
            self.section_layer.selected_traces = []
        
        # create section undo/redo state object if needed
        if new_section_num not in self.series_states:
            self.series_states[new_section_num] = SectionStates(self.section)
        
        # reload trace list
        if self.trace_table_manager:
            self.trace_table_manager.loadSection(self.section)
        
        # propogate transform if requested
        if self.propogate_tform and new_section_num not in self.propogated_sections:
            current_tform = self.section.tforms[self.series.alignment]
            new_tform = self.stored_tform * current_tform
            self.section_layer.changeTform(new_tform)
            self.propogated_sections.append(new_section_num)

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
        tform = self.section.tforms[self.series.alignment]
        min_x, min_y, max_x, max_y = trace.getBounds(tform)
        range_x = max_x - min_x
        range_y = max_y - min_y
        self.series.window = [min_x - range_x/2, min_y - range_y/2, range_x * 2, range_y * 2]

        # set the trace as the only selected trace
        self.section_layer.selected_traces = [trace]

        self.generateView()
    
    def findContour(self, contour_name : str):
        """Focus the window view on a given trace.
        
            Params:
                contour_name (str): the name of the contour to focus on
        """
        # check if contour exists
        if contour_name not in self.section.contours or self.section.contours[contour_name].isEmpty():
            return
        
        # get the bounds of the contour and set the window
        contour = self.section.contours[contour_name]
        tform = self.section.tforms[self.series.alignment]
        vals = [trace.getBounds(tform) for trace in contour]
        min_x = min([v[0] for v in vals])
        min_y = min([v[1] for v in vals])
        max_x = max([v[2] for v in vals])
        max_y = max([v[3] for v in vals])
        range_x = max_x - min_x
        range_y = max_y - min_y
        self.series.window = [min_x - range_x/2, min_y - range_y/2, range_x * 2, range_y * 2]

        # set the selected traces
        self.section_layer.selected_traces = contour.getTraces()

        self.generateView()
    
    def home(self):
        """Set the view to the image."""
        # check is an image has been loaded
        if not self.section_layer.image_found:
            return
        
        tform = self.section.tforms[self.series.alignment]
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
        if trace in self.section_layer.selected_traces:
            self.section_layer.selected_traces.remove(trace)
        else:
            self.section_layer.selected_traces.append(trace)

        self.generateView(generate_image=False)
    
    def selectTraces(self, traces : list[Trace]):
        """Select/deselect a set of traces.
        
            Params:
                traces (list[Trace]): the traces to select
        """
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return
        
        traces_to_add = []
        for trace in traces:
            if trace not in self.section_layer.selected_traces:
                traces_to_add.append(trace)
        if traces_to_add:
            self.section_layer.selected_traces += traces_to_add
        else:
            for trace in traces:
                self.section_layer.selected_traces.remove(trace)
            
        self.generateView(generate_image=False)
    
    def changeAlignment(self, new_alignment : str):
        """Change the alignment setting for the series.
        
            Params:
                new_alignment (str): the name of the new alignment
        """
        self.series.alignment = new_alignment

        # turn off propogation
        self.setPropogationMode(False)
        
        self.reload()

        # refresh all of the tables
        if self.obj_table_manager:
            self.obj_table_manager.refresh()
        if self.trace_table_manager:
            self.trace_table_manager.loadSection()
        if self.ztrace_table_manager:
            self.ztrace_table_manager.refresh()
    
    def translateTform(self, dx : float, dy : float):
        """Trnaslate the transform for the entire section.
            Params:
                dx (float): x-translate
                dy (float): y-translate
        """
        new_tform = self.section.tforms[self.series.alignment].getList()
        new_tform[2] += dx
        new_tform[5] += dy
        new_tform = Transform(new_tform)
        self.changeTform(new_tform)
    
    def translate(self, dx : float, dy : float):
        """Translate the transform OR the selected traces.
        
            Params:
                dx (float): x-translate
                dy (float): y-translate
        """
        if self.section_layer.selected_traces:
            self.section_layer.translateTraces(dx, dy)
            self.generateView()
            self.saveState()
        else:
            self.translateTform(dx, dy)
    
    def resizeWindow(self, pixmap_dim : tuple):
        """Convert the window to match the proportions of the pixmap.
        
            Params:
                pixmap_dim (tuple): the w and h of the pixmap view
        """
        # get dimensions of field window and pixmap
        window_x, window_y, window_w, window_h = tuple(self.series.window)
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
        self.generateView(generate_image=False)
    
    def toggleShowAllTraces(self):
        """Toggle show all traces regardless of hiding status."""
        self.show_all_traces = not self.show_all_traces
        if self.show_all_traces:
            self.hide_trace_layer = False
        self.generateView(generate_image=False)
    
    def linearAlign(self):
        """Modify the linear transformation using points from the selected trace.
        """
        if not self.b_section:
            return
        
        # gather traces
        a_traces = self.section_layer.selected_traces.copy()
        b_traces = self.b_section_layer.selected_traces.copy()

        # check number of selected traces
        alen = len(a_traces)
        blen = len(b_traces)
        if alen != blen or alen < 3:
            return
        contour_name = a_traces[0].name

        # check that all traces have same name
        for trace in (a_traces + b_traces):
            if trace.name != contour_name:
                return

        # gather points from each section
        centsA = []
        for trace in self.section.contours[contour_name]:
            if trace in a_traces:
                centsA.append(centroid(trace.points))
        centsB = []
        tformB = self.b_section.tforms[self.series.alignment]
        for trace in self.b_section.contours[contour_name]:
            if trace in b_traces:
                pts = tformB.map(trace.points)
                centsB.append(centroid(pts))
        
        # calculate the tform
        a2b_tform = estimateLinearTform(centsA, centsB)

        # change the transform
        self.changeTform(a2b_tform)

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
            show_all_traces=self.show_all_traces
        )

        # blend b section if requested
        if blend and self.b_section is not None:
            # generate b section view
            b_view = self.b_section_layer.generateView(
                pixmap_dim,
                self.series.window,
                generate_image=generate_image,
                generate_traces=generate_traces,
                hide_traces=self.hide_trace_layer
            )
            # overlay a and b sections
            painter = QPainter(view)
            painter.setOpacity(0.5)
            painter.drawPixmap(0, 0, b_view)
            painter.end()
        
        return view
    
    # CONNECT SECTIONVIEW FUNCTIONS TO FIELDVIEW CLASS

    def deleteTraces(self, traces=None):
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return
        self.section_layer.deleteTraces(traces)
        self.saveState()
        self.generateView(generate_image=False)
    
    def mergeSelectedTraces(self):
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return
        self.section_layer.mergeSelectedTraces()
        self.saveState()
        self.generateView(generate_image=False)
    
    def cutTrace(self, scalpel_trace):
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return
        self.section_layer.cutTrace(scalpel_trace)
        self.saveState()
        self.generateView(generate_image=False)
    
    def newTrace(self, pix_trace, tracing_trace, closed=True):
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            self.generateView(generate_image=False)
            return
        self.section_layer.newTrace(pix_trace, tracing_trace, closed=closed)
        self.saveState()
        self.generateView(generate_image=False)
    
    def placeStamp(self, pix_x, pix_y, stamp):
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return
        self.section_layer.placeStamp(pix_x, pix_y, stamp)
        self.saveState()
        self.generateView(generate_image=False)
    
    def findClosestTrace(self, field_x, field_y, radius=0.5):
        return self.section_layer.findClosestTrace(field_x, field_y, radius)
    
    def deselectAllTraces(self):
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return
        self.section_layer.deselectAllTraces()
        self.generateView(generate_image=False)
    
    def selectAllTraces(self):
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return
        self.section_layer.selectAllTraces()
        self.generateView(generate_image=False)
    
    def hideTraces(self, traces=None, hide=True):
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return
        self.section_layer.hideTraces(traces, hide)
        self.saveState()
        self.generateView(generate_image=False)
    
    def unhideAllTraces(self):
        if self.hide_trace_layer:
            self.hide_trace_layer = False
        self.section_layer.unhideAllTraces()
        self.saveState()
        self.generateView(generate_image=False)
    
    def makeNegative(self, negative=True):
        self.section_layer.makeNegative(negative)
        self.saveState()
    
    def changeBrightness(self, change):
        self.section_layer.changeBrightness(change)
        self.generateView(generate_traces=False)
    
    def changeContrast(self, change):
        self.section_layer.changeContrast(change)
        self.generateView(generate_traces=False)
    
    def changeTform(self, new_tform):
        # check for section locked status
        if self.section.align_locked:
            return

        # check if propogating
        if self.propogate_tform:
            current_tform = self.section_layer.section.tforms[self.series.alignment]
            dtform = new_tform * current_tform.inverted()
            self.stored_tform = dtform * self.stored_tform

        self.section_layer.changeTform(new_tform)
        self.saveState()
        self.generateView()
    
    def copy(self):
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return
        self.clipboard = self.section_layer.getCopiedTraces()
    
    def cut(self):
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return
        self.clipboard = self.section_layer.getCopiedTraces(cut=True)
        self.saveState()
        self.generateView(generate_image=False)
    
    def paste(self):
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return
        self.section_layer.pasteTraces(self.clipboard)
        self.saveState()
        self.generateView(generate_image=False)
    
    def pasteAttributes(self):
        # disable if trace layer is hidden
        if self.hide_trace_layer:
            return
        self.section_layer.pasteAttributes(self.clipboard)
        self.saveState()
        self.generateView(generate_image=False)
    
    
