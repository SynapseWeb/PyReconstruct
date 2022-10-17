from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPixmap, QPen, QColor, QTransform, QPainter, QPolygon

from modules.recon.section import Section
from modules.recon.trace import Trace

from modules.gui.attributedialog import AttributeDialog

from modules.calc.grid import getExterior, mergeTraces, reducePoints, cutTraces
from modules.calc.quantification import getDistanceFromTrace
from modules.calc.pfconversions import pixmapPointToField, fieldPointToPixmap

class TraceLayer():

    def __init__(self, section : Section):
        """Create a trace layer.
        
            Params:
                traces (list): the existing trace list (from a Section object)
        """
        self.section = section
        self.selected_traces = []
        self.all_traces_hidden = False
    
    def findClosestTrace(self, field_x : float, field_y : float, radius=0.5) -> Trace:
        """Find closest trace to field coordinates in a given radius.
        
            Params:
                field_x (float): x coordinate of search center
                field_y (float): y coordinate of search center
                radius (float): 1/2 of the side length of search square
            
            Returns:
                (Trace) the trace closest to the center
                None if no trace points are found within the radius
        """
        min_distance = -1
        closest_trace = None
        t = self.section.tform
        point_tform = QTransform(t[0], t[3], t[1], t[4], t[2], t[5]) # normal matrix for points
        for trace in self.section.traces:
            if trace.hidden:
                continue
            points = []
            for point in trace.points:
                x, y = point_tform.map(*point)
                points.append((x,y))
            dist = getDistanceFromTrace(field_x, field_y, points, factor=1/self.section.mag)
            if closest_trace is None or dist < min_distance:
                min_distance = dist
                closest_trace = trace
        return closest_trace if min_distance <= radius else None
    
    def selectTrace(self, pix_x, pix_y, deselect=False):
        """"Select the closest trace to the given field coordinates.
        
            Params:
                field_x (float): the x-coord of the point in the field
                field_y (float): the y-coord of the point in the field
        """
        field_x, field_y = pixmapPointToField(pix_x, pix_y, self.pixmap_dim, self.window, self.section.mag)
        # calculate radius based on window size (2% of window size)
        window_size = max(self.window[2:])
        radius = window_size / 25
        selected = self.findClosestTrace(field_x, field_y, radius=radius)
        if selected is not None:
            if not deselect:
                self.selected_traces.append(selected)
                return True
            elif deselect and selected in self.selected_traces:
                self.selected_traces.remove(selected)
                return True
        return False

    def newTrace(self, pix_trace : list, name, color, closed=True):
        """Create a new trace from pixel coordinates.
        
            Params:
                pix_trace (list): pixel coordinates for the new trace
                closed (bool): whether or not the new trace is closed
        """
        if len(pix_trace) < 1:  # do not create a new trace if there is only one point
            return
        if closed:
            pix_trace = getExterior(pix_trace)  # get exterior if closed (will reduce points)
        else:
            pix_trace = reducePoints(pix_trace, closed=False)  # only reduce points if trace is open
        new_trace = Trace(name, color, closed=closed)
        t = self.section.tform
        point_tform = QTransform(t[0], t[3], t[1], t[4], t[2], t[5]) # normal matrix for points
        for point in pix_trace:
            field_point = pixmapPointToField(point[0], point[1], self.pixmap_dim, self.window, self.section.mag)
            rtform_point = point_tform.inverted()[0].map(*field_point) # apply the inverse tform to fix trace to base image
            new_trace.add(rtform_point)
        self.section.traces.append(new_trace)
        self.selected_traces.append(new_trace)
    
    def placeStamp(self, pix_x : int, pix_y : int, trace : Trace):
        """Called when mouse is pressed in stamp mode.
        
        Creates a stamp centered on the mouse location.
        
            Params:
                pix_x (int): pixel x-coord to place stamp
                pix_y (int): pixel y-coord to place stamp
                trace (Trace): the trace to place down
        """
        # get mouse coords and convert to field coords
        field_x, field_y = pixmapPointToField(pix_x, pix_y, self.pixmap_dim, self.window, self.section.mag)
        # create new stamp trace
        t = self.section.tform
        point_tform = QTransform(t[0], t[3], t[1], t[4], t[2], t[5])
        new_trace = Trace(trace.name, trace.color)
        for point in trace.points:
            field_point = (point[0] + field_x, point[1] + field_y)
            rtform_point = point_tform.inverted()[0].map(*field_point)  # fix the coords to image
            new_trace.add(rtform_point)
        self.section.traces.append(new_trace)
        self.selected_traces.append(new_trace)
        
    def changeTraceAttributes(self):
        """Open a dialog to change the name and/or color of a trace."""
        if len(self.selected_traces) == 0:  # skip if no traces selected
            return
        name = self.selected_traces[0].name
        color = self.selected_traces[0].color
        for trace in self.selected_traces[1:]:
            if trace.name != name:
                name = ""
            if trace.color != color:
                color = None
        attr_input = AttributeDialog(parent=self, name=name, color=color).exec_()
        if attr_input is None:
            return
        new_name, new_color = attr_input
        for trace in self.selected_traces:
            if new_name != "":
                trace.name = new_name
            if new_color is not None:
                trace.color = new_color
    
    def deselectAllTraces(self):
        """Deselect all traces."""
        self.selected_traces = []
    
    def hideSelectedTraces(self):
        """Hide all selected traces."""
        for trace in self.selected_traces:
            trace.setHidden(True)
        self.selected_traces = []
    
    def mergeSelectedTraces(self):
        """Merge all selected traces."""
        if len(self.selected_traces) < 2:
            print("Cannot merge fewer than two traces.")
            return
        traces = []
        first_trace = self.selected_traces[0]
        name = first_trace.name
        color = first_trace.color  # use color of first trace selected
        for trace in self.selected_traces:
            if trace.closed == False:
                print("Can only merge closed traces.")
                return
            if trace.name != name:
                print("Cannot merge differently named traces.")
                return
            # collect pixel values for trace points
            traces.append([])
            t = self.section.tform
            point_tform = QTransform(t[0], t[3], t[1], t[4], t[2], t[5]) # normal matrix for points
            for point in trace.points:
                x, y = tuple(point)
                x, y = point_tform.map(x, y)
                x, y = fieldPointToPixmap(x, y, self.window, self.pixmap_dim, self.section.mag)
                traces[-1].append((x, y))
        merged_traces = mergeTraces(traces)  # merge the pixel traces
        # create new merged trace
        self.deleteSelectedTraces()
        for trace in merged_traces:
            self.newTrace(trace, name=name, color=color)
    
    def cutTrace(self, scalpel_trace : list):
        """Cuts the selected trace along the scalpel line.
        
            Params:
                scalpel_pix_points (list): the scalpel trace in pixmap points
        """
        if len(self.selected_traces) == 0:
            print("Please select traces you wish to cut.")
            return
        elif len(self.selected_traces) > 1:
            print("Please select only one trace to cut at a time.")
            return
        trace = self.selected_traces[0]
        name = trace.name
        color = trace.color
        trace_to_cut = []
        # establish tform
        t = self.section.tform
        point_tform = QTransform(t[0], t[3], t[1], t[4], t[2], t[5])
        for point in self.selected_traces[0].points:
            x, y = tuple(point)
            x, y = point_tform.map(x, y)
            x, y = fieldPointToPixmap(x, y, self.window, self.pixmap_dim, self.section.mag)
            trace_to_cut.append((x, y))
        cut_traces = cutTraces(trace_to_cut, scalpel_trace)  # merge the pixel traces
        # create new traces
        self.deleteSelectedTraces()
        for trace in cut_traces:
            self.newTrace(trace, name=name, color=color)
    
    def deleteSelectedTraces(self):
        """Delete selected traces.
        
            Params:
                save_state (bool): whether or not to save the state after deleting
        """
        for trace in self.selected_traces:
            self.section.traces.remove(trace)
        self.selected_traces = []
    
    def toggleHideAllTraces(self):
        """Hide/unhide every trace on the section."""
        if self.all_traces_hidden:
            for trace in self.section.traces:
                trace.setHidden(False)
            self.all_traces_hidden = False
        else:
            for trace in self.section.traces:
                trace.setHidden(True)
            self.all_traces_hidden = True
        self.selected_traces = []
    
    def _drawTrace(self, trace_layer : QPixmap, trace : Trace, highlight=False) -> bool:
        """Draw a trace on the current trace layer and return bool indicating if trace is in the current view.
        
            Params:
                trace_layer (QPixmap): the pixmap to draw the traces
                trace (Trace): the trace to draw on the pixmap
                highlight (bool): whether or not the trace is being highlighted
            Returns:
                (bool) if the trace is within the current field window view
        """
        # establish tform
        t = self.section.tform
        point_tform = QTransform(t[0], t[3], t[1], t[4], t[2], t[5])
        # set up painter
        painter = QPainter(trace_layer)
        if highlight: # create dashed white line if trace is to be highlighted
            pen = QPen(QColor(255, 255, 255), 1)
            pen.setDashPattern([2, 5])
            painter.setPen(pen)
            # # internal use: draw highlight as points
            # painter.setPen(QPen(QColor(255, 255, 255), 5))
            # for point in trace.points:
            #     x, y = self.point_tform.map(*point)
            #     x, y = self.fieldPointToPixmap(x,y)
            #     painter.drawPoint(x,y)
            # painter.end()
            # return
            # # end internal use
        else:
            painter.setPen(QPen(QColor(*trace.color), 1))
        # iterate through points and convert to screen coord points
        qpoints = []
        for point in trace.points:
            x, y = tuple(point)
            x, y = point_tform.map(x, y)
            x, y = fieldPointToPixmap(x, y, self.window, self.pixmap_dim, self.section.mag)
            qpoints.append(QPoint(x, y))
        # draw trace
        if trace.closed:
            painter.drawPolygon(qpoints)
        else:
            painter.drawPolyline(qpoints)
    
    def generateTraceLayer(self, pixmap_dim : tuple, window : list):
        """Generate the traces on a transparent background.
        
            Params:
                pixmap_dim (tuple): the w and h of the pixmap to be output
                window (list): the view of the window (x, y, w, h)
        """
        # draw all the traces
        self.window = window
        self.pixmap_dim = pixmap_dim
        pixmap_w, pixmap_h = tuple(pixmap_dim)
        trace_layer = QPixmap(pixmap_w, pixmap_h)
        trace_layer.fill(Qt.transparent)
        for trace in self.section.traces:
            if not trace.hidden:
                self._drawTrace(
                    trace_layer,
                    trace,
                )
        for trace in self.selected_traces:
            self._drawTrace(
                trace_layer,
                trace,
                highlight=True
            )  
        return trace_layer
        