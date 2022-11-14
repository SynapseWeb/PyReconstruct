from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPixmap, QPen, QColor, QTransform, QPainter

from modules.pyrecon.series import Series
from modules.pyrecon.section import Section
from modules.pyrecon.trace import Trace

from modules.backend.grid import getExterior, mergeTraces, reducePoints, cutTraces
from modules.calc.quantification import getDistanceFromTrace, pointInPoly
from modules.calc.pfconversions import pixmapPointToField, fieldPointToPixmap

class TraceLayer():

    def __init__(self, section : Section, series : Series):
        """Create a trace layer.
        
            Params:
                traces (list): the existing trace list (from a Section object)
        """
        self.section = section
        self.series = series
        self.selected_traces = []
        self.all_traces_hidden = False
    
    def traceToPix(self, trace : Trace, qpoints=False):
        """Return the set of pixel points corresponding to a trace.
        
            Params:
                trace (Trace): the trace to convert
            Returns:
                (list): list of pixel points
        """
        new_pts = []
        t = self.section.tforms[self.series.alignment]
        point_tform = QTransform(t[0], t[3], t[1], t[4], t[2], t[5])
        for point in trace.points:
            x, y = tuple(point)
            x, y = point_tform.map(x, y)
            x, y = fieldPointToPixmap(x, y, self.window, self.pixmap_dim, self.section.mag)
            if qpoints:
                new_pts.append(QPoint(x, y))
            else:
                new_pts.append((x, y))
        return new_pts
    
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
        t = self.section.tforms[self.series.alignment]
        point_tform = QTransform(t[0], t[3], t[1], t[4], t[2], t[5]) # normal matrix for points
        for trace in self.traces_in_view:
            points = []
            for point in trace.points:
                x, y = point_tform.map(*point)
                points.append((x,y))
            dist = getDistanceFromTrace(field_x, field_y, points, factor=1/self.section.mag)
            if closest_trace is None or dist < min_distance:
                min_distance = dist
                closest_trace = trace
        return closest_trace if min_distance <= radius else None
    
    def getTrace(self, pix_x, pix_y) -> Trace:
        """"Return the closest trace to the given field coordinates.
        
            Params:
                field_x (float): the x-coord of the point in the field
                field_y (float): the y-coord of the point in the field
            Returns:
                (Trace): the closest trace
        """
        field_x, field_y = pixmapPointToField(pix_x, pix_y, self.pixmap_dim, self.window, self.section.mag)
        # calculate radius based on window size (2% of window size)
        window_size = max(self.window[2:])
        radius = window_size / 100
        return self.findClosestTrace(field_x, field_y, radius=radius)
    
    def getTraces(self, pix_poly : list) -> list[Trace]:
        """"Select all traces that are at least partially in a polygon
        
            Params:
                pix_poly (list): a list of screen points
            Returns:
                (list[Trace]): the list of traces within the polygon
        """
        traces_in_poly = []
        for trace in self.traces_in_view:
            pix_points = self.traceToPix(trace)
            for point in pix_points:
                if pointInPoly(*point, pix_poly):
                    traces_in_poly.append(trace)
                    break
        return traces_in_poly

    def newTrace(self, pix_trace : list, base_trace : Trace, closed=True):
        """Create a new trace from pixel coordinates.
        
            Params:
                pix_trace (list): pixel coordinates for the new trace
                base_trace (Trace): the trace containing the desired attributes
                closed (bool): whether or not the new trace is closed
        """
        if len(pix_trace) < 1:  # do not create a new trace if there is only one point
            return
        if closed:
            pix_trace = getExterior(pix_trace)  # get exterior if closed (will reduce points)
        else:
            pix_trace = reducePoints(pix_trace, closed=False)  # only reduce points if trace is open

        # create the new trace
        new_trace = base_trace.copy()
        new_trace.closed = closed
        new_trace.points = []

        # get the points
        t = self.section.tforms[self.series.alignment]
        point_tform = QTransform(t[0], t[3], t[1], t[4], t[2], t[5]) # normal matrix for points
        for point in pix_trace:
            field_point = pixmapPointToField(point[0], point[1], self.pixmap_dim, self.window, self.section.mag)
            rtform_point = point_tform.inverted()[0].map(*field_point) # apply the inverse tform to fix trace to base image
            new_trace.add(rtform_point)
        
        self.section.addTrace(new_trace)
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
        t = self.section.tforms[self.series.alignment]
        point_tform = QTransform(t[0], t[3], t[1], t[4], t[2], t[5])
        new_trace = Trace(trace.name, trace.color)
        for point in trace.points:
            field_point = (point[0] + field_x, point[1] + field_y)
            rtform_point = point_tform.inverted()[0].map(*field_point)  # fix the coords to image
            new_trace.add(rtform_point)
        self.section.addTrace(new_trace)
        self.selected_traces.append(new_trace)
        
    def changeTraceAttributes(self, name : str = None, color : tuple = None, tags : set = None):
        """Change the name and/or color of a trace.
        
            Params:
                name (str): the new name
                color (tuple): the new color
                tags (set): the new set of tags
        """
        # change object attributes
        for trace in self.selected_traces:
            self.section.removeTrace(trace)
            if color:
                trace.color = color
            if tags:
                trace.tags = tags
            if name:
                trace.name = name
            self.section.addTrace(trace)
    
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
        for trace in self.selected_traces:
            if trace.closed == False:
                print("Can only merge closed traces.")
                return
            if trace.name != name:
                print("Cannot merge differently named traces.")
                return
            # collect pixel values for trace points
            pix_points = self.traceToPix(trace)
            traces.append(pix_points)
        merged_traces = mergeTraces(traces)  # merge the pixel traces
        # create new merged trace
        self.deleteSelectedTraces()
        for trace in merged_traces:
            self.newTrace(trace, first_trace)
    
    def cutTrace(self, knife_trace : list):
        """Cuts the selected trace along the knife line.
        
            Params:
                knife_pix_points (list): the knife trace in pixmap points
        """
        if len(self.selected_traces) == 0:
            print("Please select traces you wish to cut.")
            return
        elif len(self.selected_traces) > 1:
            print("Please select only one trace to cut at a time.")
            return
        trace = self.selected_traces[0]
        trace_to_cut = self.traceToPix(trace)
        cut_traces = cutTraces(trace_to_cut, knife_trace)  # merge the pixel traces
        # create new traces
        self.deleteSelectedTraces()
        for piece in cut_traces:
            self.newTrace(piece, trace)
    
    def deleteSelectedTraces(self):
        """Delete selected traces.
        
            Params:
                save_state (bool): whether or not to save the state after deleting
        """
        for trace in self.selected_traces:
            self.section.removeTrace(trace)
        self.selected_traces = []
    
    def eraseArea(self, pix_x, pix_y):
        """Erase an area of the field.
        
            Params:
                pix_x: the x coord for erasing
                pix_y: the y coord for erasing
        """
        trace = self.getTrace(pix_x, pix_y)
        if trace in self.selected_traces:
            self.section.removeTrace(trace)
            self.selected_traces.remove(trace)
            return True
        return False
    
    def toggleHideAllTraces(self):
        """Hide/unhide every trace on the section."""
        if self.all_traces_hidden:
            for trace in self.section.tracesAsList():
                trace.setHidden(False)
            self.all_traces_hidden = False
        else:
            for trace in self.section.tracesAsList():
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
        t = self.section.tforms[self.series.alignment]
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
        
        # convert to screen coord points
        qpoints = self.traceToPix(trace, qpoints=True)

        # check if the trace is actually in the view
        trace_in_view = False
        for point in qpoints:
            if pointInPoly(point.x(), point.y(), self.screen_poly):
                trace_in_view = True
                break

        # draw trace
        if trace.closed:
            painter.drawPolygon(qpoints)
        else:
            painter.drawPolyline(qpoints)
        
        return trace_in_view
    
    def generateTraceLayer(self, pixmap_dim : tuple, window : list):
        """Generate the traces on a transparent background.
        
            Params:
                pixmap_dim (tuple): the w and h of the pixmap to be output
                window (list): the view of the window (x, y, w, h)
        """
        # draw all the traces
        self.window = window
        self.pixmap_dim = pixmap_dim
        self.screen_poly = [
            (0, 0),
            (self.pixmap_dim[0], 0),
            (self.pixmap_dim[0], self.pixmap_dim[1]),
            (0, self.pixmap_dim[1])
        ]
        pixmap_w, pixmap_h = tuple(pixmap_dim)
        trace_layer = QPixmap(pixmap_w, pixmap_h)
        trace_layer.fill(Qt.transparent)

        # draw traces (keep track of those in view)
        self.traces_in_view = []
        for trace in self.section.tracesAsList():
            if not trace.hidden:
                trace_in_view = self._drawTrace(
                    trace_layer,
                    trace,
                )
                if trace_in_view:
                    self.traces_in_view.append(trace)
        
        # draw highlights
        for trace in self.selected_traces:
            self._drawTrace(
                trace_layer,
                trace,
                highlight=True
            )  
        return trace_layer
        