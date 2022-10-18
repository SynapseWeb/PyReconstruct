from PySide6.QtGui import QPainter

from modules.recon.series import Series

from modules.gui.backend.section_layer import SectionLayer

class FieldState():

    def __init__(self, traces : list, tform : list):
        """Create a field state with traces and the transform"""
        self.traces = []
        for trace in traces:
            self.traces.append(trace.copy())
        self.tform = tform.copy()
    
    def getTraces(self):
        return self.traces.copy()
    
    def getTform(self):
        return self.tform.copy()

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

        # get image dir
        if self.series.src_dir == "":
            self.src_dir = self.series.getwdir()
        else:
            self.src_dir = self.series.src_dir

        # create section view
        self.section_layer = SectionLayer(self.section, self.src_dir)

        # b section and view placeholder
        self.b_section = None
        self.b_section_layer = None

        self.undo_states = {}
        self.current_state = FieldState(self.section.traces, self.section.tform)
        self.undo_states[self.series.current_section] = []
        self.redo_states = []
    
    def reload(self):
        self.__init__(self.series)

    def saveState(self):
        """Save the current traces and transform."""
        state_list = self.undo_states[self.series.current_section]
        state_list.append(self.current_state)
        if len(state_list) > 20:  # limit the number of undo states
            state_list.pop(0)
        self.current_state = FieldState(self.section.traces, self.section.tform)
        self.redo_states = []
    
    def restoreState(self, state : FieldState):
        """Restore traces and transforms from a field state.
        
            Params:
                state (FieldState): the field state to restore
        """
        self.current_state = state
        self.section_layer.changeTform(state.getTform())
        self.section.traces = state.getTraces()
        self.section_layer.selected_traces = []
        self.generateView()

    def undoState(self):
        """Undo last action (switch to last state)."""
        state_list = self.undo_states[self.series.current_section]
        if len(state_list) >= 1:
            self.redo_states.append(self.current_state)
            self.restoreState(state_list.pop())
    
    def redoState(self):
        """Redo an undo (switch to last undid state)."""
        state_list = self.undo_states[self.series.current_section]
        if len(self.redo_states) >= 1:
            state_list.append(self.current_state)
            self.restoreState(self.redo_states.pop())
    
    def swapABsections(self):
        """Switch the A and B sections."""
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
            self.section_layer = SectionLayer(self.section, self.src_dir)
            # set new current section
            self.series.current_section = new_section_num
            # clear selected traces
            self.section_layer.selected_traces = []
        # clear redo states
        self.redo_states = []
        # create new list for states if needed
        if new_section_num not in self.undo_states:
            self.undo_states[new_section_num] = []
        # generate view and update status bar
        self.generateView()
    
    def findTrace(self, trace_name : str, occurence=1):
        """Focus the window view on a given trace.
        
            Params:
                trace_name (str): the name of the trace to focus on
                occurence (int): find the nth trace on the section"""
        count = 0
        for trace in self.section.traces:
            if trace.name == trace_name:
                count += 1
                if count == occurence:
                    min_x, min_y, max_x, max_y = trace.getBounds(self.point_tform)
                    range_x = max_x - min_x
                    range_y = max_y - min_y
                    self.series.window = [min_x - range_x/2, min_y - range_y/2, range_x * 2, range_y * 2]
                    self.selected_traces = [trace]
                    self.generateView(save_state=False)
    
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
    
    def newTrace(self, pix_trace, name, color, closed=True):
        self.section_layer.newTrace(pix_trace, name, color, closed)
        self.saveState()
        self.generateView(generate_image=False)
    
    def placeStamp(self, pix_x, pix_y, stamp):
        self.section_layer.placeStamp(pix_x, pix_y, stamp)
        self.saveState()
        self.generateView(generate_image=False)
    
    def findClosestTrace(self, field_x, field_y, radius=0.5):
        return self.section_layer.findClosestTrace(field_x, field_y, radius)
    
    def selectTrace(self, pix_x, pix_y, deselect=False):
        requires_update = self.section_layer.selectTrace(pix_x, pix_y, deselect=deselect)
        if requires_update:
            self.generateView(generate_image=False)
    
    def deselectAllTraces(self):
        self.section_layer.deselectAllTraces()
        self.generateView(generate_image=False)
    
    def hideSelectedTraces(self):
        self.section_layer.hideSelectedTraces()
        self.saveState()
        self.generateView(generate_image=False)
    
    def toggleHideAllTraces(self):
        self.section_layer.toggleHideAllTraces
        self.generateView(generate_image=False)
    
    def changeTraceAttributes(self):
        self.section_layer.changeTraceAttributes()
        self.saveState()
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
    
    
