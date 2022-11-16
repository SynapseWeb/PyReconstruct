from PySide6.QtGui import QPainter, QTransform

from modules.pyrecon.series import Series

from modules.backend.section_layer import SectionLayer
from modules.backend.state_manager import SectionStates

class FieldView():

    def __init__(self, series : Series):
        """Create the field view object.
        
            Params:
                series (Series): the series object
                wdir (str): the working directory for the series
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
        self.trace_table_manager = None
    
    def reload(self):
        """Reload the section data (used if section files were modified)."""
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
        self.generateView()
    
    def reloadImage(self):
        """Reload the section images."""
        self.section_layer.loadImage()
        if self.b_section is not None:
            self.b_section_layer.loadImage()

    def saveState(self):
        """Save the current traces and transform.
        
        ALSO updates the lists.
        """
        section_states = self.series_states[self.series.current_section]
        section_states.addState(self.section)
        if self.obj_table_manager:
            self.obj_table_manager.updateSection(
                self.section,
                self.series.current_section
            )
        if self.trace_table_manager:
            self.trace_table_manager.update()
        self.section.clearTracking()

    def undoState(self):
        """Undo last action (switch to last state)."""
        self.section_layer.selected_traces = []
        section_states = self.series_states[self.series.current_section]
        modified_contours = section_states.undoState(self.section)
        if modified_contours is None:
            return
        if self.obj_table_manager:
            for contour in modified_contours:
                self.obj_table_manager.updateContour(
                    contour,
                    self.section,
                    self.series.current_section
                )
        if self.trace_table_manager:
            self.trace_table_manager.loadSection()
        self.generateView()
    
    def redoState(self):
        """Redo an undo (switch to last undid state)."""
        self.section_layer.selected_traces = []
        section_states = self.series_states[self.series.current_section]
        modified_contours = section_states.redoState(self.section)
        if modified_contours is None:
            return
        if self.obj_table_manager:
            for contour in modified_contours:
                self.obj_table_manager.updateContour(
                    contour,
                    self.section,
                    self.series.current_section
                )
        if self.trace_table_manager:
            self.trace_table_manager.loadSection()
        self.generateView()
    
    def swapABsections(self):
        """Switch the A and B sections."""
        self.series.current_section, self.b_section_number = self.b_section_number, self.series.current_section
        self.section, self.b_section = self.b_section, self.section
        self.section_layer, self.b_section_layer = self.b_section_layer, self.section_layer
    
    def changeSection(self, new_section_num : int):
        """Change the displayed section.
        
            Params:
                new_section_num (int): the new section number
        """
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
        
        # create section state object if needed
        if new_section_num not in self.series_states:
            self.series_states[new_section_num] = SectionStates(self.section)
        
        # reload trace list
        if self.trace_table_manager:
            self.trace_table_manager.loadSection(self.section)

        # generate view and update status bar
        self.generateView()
    
    def findTrace(self, trace_name : str, index=0):
        """Focus the window view on a given trace.
        
            Params:
                trace_name (str): the name of the trace to focus on
                index (int): find the nth trace on the section
        """
        if trace_name not in self.section.contours or len(self.section.contours[trace_name]) == 0:
            return
        try:
            trace = self.section.contours[trace_name][index]
        except IndexError:
            return
        t = self.section.tforms[self.series.alignment]
        min_x, min_y, max_x, max_y = trace.getBounds(t)
        range_x = max_x - min_x
        range_y = max_y - min_y
        self.series.window = [min_x - range_x/2, min_y - range_y/2, range_x * 2, range_y * 2]
        self.section_layer.selected_traces = [trace]
        self.generateView()
    
    def resizeWindow(self, pixmap_dim : tuple):
        """Convert the window to match the proportions of the pixmap.
        
            Params:
                pixmap_dim (tuple): the w and h of the pixmap view"""
        # get dimensions of field window and pixmap
        # resize window to match proportions of current geometry
        window_x, window_y, window_w, window_h = tuple(self.series.window)
        pixmap_w, pixmap_h = tuple(pixmap_dim)
        window_ratio = window_w/window_h
        pixmap_ratio = pixmap_w / pixmap_h
        if abs(window_ratio - pixmap_ratio) > 1e-6:
            if window_ratio < pixmap_ratio:  # increase the width
                new_w = window_h * pixmap_ratio
                new_x = window_x - (new_w - window_w) / 2
                window_w = new_w
                window_x = new_x
            else: # increase the height
                new_h = window_w / pixmap_ratio
                new_y = window_y - (new_h - window_h) / 2
                window_h = new_h
                window_y = new_y
            self.series.window = [window_x, window_y, window_w, window_h]

    def generateView(self, pixmap_dim : tuple, generate_image=True, generate_traces=True, blend=False):
        """Generate the view seen by the user in the main window.
        
            Params:
                pixmap_dim (tuple): the w and h of the pixmap view
                generate_image (bool): whether or not to redraw the image
                generate_traces (bool): whether or not to redraw the traces
        """
        # resize series window to match view proportions
        self.resizeWindow(pixmap_dim)
        # generate section view
        view = self.section_layer.generateView(
            pixmap_dim,
            self.series.window,
            generate_image=generate_image,
            generate_traces=generate_traces
        )
        # blend b section if requested
        if blend and self.b_section is not None:
            # generate b section view
            b_view = self.b_section_layer.generateView(
                pixmap_dim,
                self.series.window,
                generate_image=generate_image,
                generate_traces=generate_traces
            )
            # overlay a and b sections
            painter = QPainter(view)
            painter.setOpacity(0.5)
            painter.drawPixmap(0, 0, b_view)
            painter.end()
        
        return view
    
    # CONNECT SECTIONVIEW FUNCTIONS TO FIELDVIEW CLASS
    # look up a better way to do this??

    def deleteSelectedTraces(self):
        self.section_layer.deleteSelectedTraces()
        self.saveState()
        self.generateView(generate_image=False)
    
    def mergeSelectedTraces(self):
        self.section_layer.mergeSelectedTraces()
        self.saveState()
        self.generateView(generate_image=False)
    
    def cutTrace(self, scalpel_trace):
        self.section_layer.cutTrace(scalpel_trace)
        self.saveState()
        self.generateView(generate_image=False)
    
    def newTrace(self, pix_trace, tracing_trace, closed=True):
        self.section_layer.newTrace(pix_trace, tracing_trace, closed=closed)
        self.saveState()
        self.generateView(generate_image=False)
    
    def placeStamp(self, pix_x, pix_y, stamp):
        self.section_layer.placeStamp(pix_x, pix_y, stamp)
        self.saveState()
        self.generateView(generate_image=False)
    
    def findClosestTrace(self, field_x, field_y, radius=0.5):
        return self.section_layer.findClosestTrace(field_x, field_y, radius)
    
    def selectTrace(self, trace):
        if not trace:
            return
        if trace in self.section_layer.selected_traces:
            self.section_layer.selected_traces.remove(trace)
        else:
            self.section_layer.selected_traces.append(trace)
        self.generateView(generate_image=False)
    
    def selectTraces(self, traces):
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
    
    def deselectAllTraces(self):
        self.section_layer.deselectAllTraces()
        self.generateView(generate_image=False)
    
    def hideSelectedTraces(self):
        self.section_layer.hideSelectedTraces()
        self.saveState()
        self.generateView(generate_image=False)
    
    def toggleHideAllTraces(self):
        self.section_layer.toggleHideAllTraces()
        self.generateView(generate_image=False)
    
    def changeBrightness(self, change):
        self.section_layer.changeBrightness(change)
        self.generateView(generate_traces=False)
    
    def changeContrast(self, change):
        self.section_layer.changeContrast(change)
        self.generateView(generate_traces=False)
    
    def changeTform(self, new_tform):
        self.section_layer.changeTform(new_tform)
        self.saveState()
        self.generateView()
    
    def changeAlignment(self, new_alignment):
        self.series.alignment = new_alignment
        self.generateView()
    
    
