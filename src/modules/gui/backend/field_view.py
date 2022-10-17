from PySide6.QtGui import QPixmap, QPainter

from modules.recon.series import Series

from modules.gui.backend.image_layer import ImageLayer
from modules.gui.backend.trace_layer import TraceLayer

class FieldState():

    def __init__(self, traces : list, tform : list):
        """Create a field state with traces and the transform"""
        self.traces = []
        for trace in traces:
            self.trace.append(trace.copy())
        self.tform = tform.copy()

class FieldView(ImageLayer, TraceLayer):

    def __init__(self, series : Series):
        """Create the field view object.
        
            Params:
                series (Series): the series object
                wdir (str): the working directory for the series
        """
        self.series = series
        self.section = self.series.loadSection(self.series.current_section)
        self.b_section = None

        ImageLayer().__init__(self.section, self.series.src_dir)
        TraceLayer().__init__(self.section)

        self.states = {}
        self.current_state = FieldState(self.section.traces, self.section.tform)
        self.states[self.series.current_section] = []
        self.redo_states = []
    
    def executeOnB(self, function):
        # swap the sections, perform function, swap the sections
        self.section, self.b_section = self.b_section, self.section
        ret = function()
        self.section, self.b_section = self.b_section, self.section
        return ret
    
    def saveState(self):
        """Save the current traces and transform."""
        state_list = self.states[self.series.current_section]
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
        self.changeTform(state.tform)
        self.section.traces = state.traces
        self.selected_traces = []

    def undoState(self):
        """Undo last action (switch to last state)."""
        state_list = self.states[self.series.current_section]
        if len(state_list) >= 1:
            self.redo_states.append(self.current_state)
            self.restoreState(state_list.pop())
    
    def redoState(self):
        """Redo an undo (switch to last undid state)."""
        state_list = self.states[self.series.current_section]
        if len(self.redo_states) >= 1:
            state_list.append(self.current_state)
            self.restoreState(self.redo_states.pop())
    
    def changeSection(self, new_section_num : int):
        """Change the displayed section.
        
            Params:
                new_section_num (int): the new section number
        """
        if new_section_num not in self.series.sections:
            return
        if new_section_num == self.b_section_number:
            # switch section and b_section if requested
            self.section, self.b_section = self.b_section, self.section
        else:
            # move primary section data to b section data
            self.b_section = self.section
            # create new section
            self.section = self.series.loadSection(new_section_num)
        # clear redo states
        self.redo_states = []
        # set new current section and b section number
        self.b_section_number = self.series.current_section
        self.series.current_section = new_section_num
    
    def reloadSection(self):
        """Reload Section trace data from file (if file was changed)."""
        self.section = self.series.loadSection(self.series.current_section)
        self.changeTform(self.section.tform)
        self.selected_traces = []
        if self.b_section is not None:
            self.b_section = self.series.loadSection(self.b_section_number)
            self.executeOnB(lambda : self.changeTform(self.b_section.tform))
    
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
        if abs(window_ratio - pixmap_ratio) > 1e-5:
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

    def generateView(self, pixmap_dim : tuple, generate_image=True, generate_traces=True, blend=False) -> QPixmap:
        """Generate the view seen by the user in the main window.
        
            Params:
                pixmap_dim (tuple): the w and h of the pixmap view
                generate_image (bool): whether or not to redraw the image
                generate_traces (bool): whether or not to redraw the traces
            Returns:
                (QPixmap): the view to be output to the screen
        """
        # resize series window to match view proportions
        self.resizeWindow()
        # generate layer pixmaps
        if generate_image:
            self.image_pixmap = self.generateImageLayer(pixmap_dim, self.series.window)
        if generate_traces:
            self.trace_pixmap = self.generateTraceLayer(pixmap_dim, self.series.window)
        # combine pixmaps
        view = self.image_pixmap.copy()
        painter = QPainter(view)
        painter.drawPixmap(0, 0, self.trace_pixmap)
        painter.end()
        # blend b section if requested
        if blend and self.b_section is not None:
            if generate_image:
                self.b_image_pixmap = self.executeOnB(
                    lambda : self.generateImageLayer(pixmap_dim, self.series.window)
                )
            if generate_traces:
                self.b_trace_pixmap = self.executeOnB(
                    lambda : self.generateTraceLayer(pixmap_dim, self.series.window)
                )
            b_view = self.b_image_pixmap.copy()
            painter = QPainter(b_view)
            painter.drawPixmap(0, 0, self.b_trace_pixmap)
            painter.end()
            # overlay a and b sections
            painter = QPainter(view)
            painter.setOpacity(0.5)
            painter.drawPixmap(0, 0, b_view)
            painter.end()
        return view
    
