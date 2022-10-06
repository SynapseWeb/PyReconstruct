import os

from PySide6.QtWidgets import (QWidget, QMainWindow)
from PySide6.QtCore import Qt, QRectF, QPoint
from PySide6.QtGui import (QPixmap, QImage, QPen, QColor, QTransform, QPainter, QPolygon)
os.environ['QT_IMAGEIO_MAXALLOC'] = "0"  # disable max image size

from modules.recon.section import Section
from modules.recon.trace import Trace

from modules.gui.attributedialog import AttributeDialog

from modules.calc.grid import getExterior, mergeTraces, reducePoints, cutTraces
from modules.calc.quantification import getDistanceFromTrace
from modules.calc.pfconversions import pixmapPointToField, fieldPointToPixmap

class TraceField():

    def __init__(self, section : Section):
        """Create a trace field.
        
            Params:
                traces (list): the existing trace list (from a Section object)
        """
        self.section = section
        self.selected_traces = []
        self.all_traces_hidden = False
    
    def addTrace(self, trace : Trace):
        """Add a trace to the trace list.
            
            Params:
                trace (Trace): the trace to add to the list
        """
        self.append(trace)
    
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
        # for trace in self.traces_within_field: # check only traces within the current window view
        for trace in self.traces:
            if trace.hidden:
                continue
            points = []
            for point in trace.points:
                x, y = self.point_tform.map(*point)
                # x, y = self.fieldPointToPixmap(x, y)
                points.append((x,y))
            dist = getDistanceFromTrace(field_x, field_y, points, factor=1/self.mag)
            if closest_trace is None or dist < min_distance:
                min_distance = dist
                closest_trace = trace
        return closest_trace if min_distance <= radius else None
    
    def selectTrace(self, field_x, field_y):
        """"Select the closest trace to the given field coordinates.
        
            Params:
                field_x (float): the x-coord of the point in the field
                field_y (float): the y-coord of the point in the field
        """
        
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
    
    def hideSelectedTraces(self):
        """Hide all selected traces."""
        for trace in self.selected_traces:
            trace.setHidden(True)
        self.selected_traces = []
    
    def toggleHideAllTraces(self):
        """Hide/unhide every trace on the section."""
        if self.all_traces_hidden:
            for trace in self.traces:
                trace.setHidden(False)
            self.all_traces_hidden = False
        else:
            for trace in self.traces:
                trace.setHidden(True)
            self.all_traces_hidden = True
        self.selected_traces = []
    
    def drawTrace(self, trace_field : QPixmap, trace : Trace, window : list, pixmap_dim : tuple, highlight=False) -> bool:
        """Draw a trace on the current trace layer and return bool indicating if trace is in the current view.
        
            Params:
                trace (Trace): the trace to draw on the pixmap
                highlight (bool): whether or not the trace is being highlighted
            Returns:
                (bool) if the trace is within the current field window view
        """
        # get window and pixmap values
        pixmap_w, pixmap_h = tuple(pixmap_dim)
        # establish tform
        t = self.section.tform
        point_tform = QTransform(t[0], t[3], t[1], t[4], t[2], t[5])
        # set up painter
        painter = QPainter(trace_field)
        within_field = False
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
        
        # establish first point
        point = trace.points[0]
        last_x, last_y = point_tform.map(*point)
        last_x, last_y = fieldPointToPixmap(last_x, last_y, window, pixmap_dim, self.section.mag)
        within_field |= 0 < last_x < pixmap_w and 0 < last_y < pixmap_h
        # connect points
        for i in range(1, len(trace.points)):
            point = trace.points[i]
            x, y = point_tform.map(*point)
            x, y = fieldPointToPixmap(x, y, window, pixmap_dim, self.section.mag)
            within_field |= 0 < x < pixmap_w and 0 < y < pixmap_h
            painter.drawLine(last_x, last_y, x, y)
            last_x = x
            last_y = y
        # connect last point to first point if closed
        if trace.closed:
            point = trace.points[0]
            x, y = point_tform.map(*point)
            x, y = fieldPointToPixmap(x, y, window, pixmap_dim, self.section.mag)
            painter.drawLine(last_x, last_y, x, y)
        painter.end()

        return within_field
    
    def generateTraceField(self, pixmap_dim : tuple, window : list) -> QPixmap:
        # draw all the traces
        pixmap_w, pixmap_h = tuple(pixmap_dim)
        trace_field = QPixmap(pixmap_w, pixmap_h)
        trace_field.fill(Qt.transparent)
        for trace in self.traces:
            if not trace.hidden:
                self.drawTrace(
                    trace_field,
                    trace,
                    window,
                    pixmap_dim
                )
        for trace in self.selected_traces:
            self.drawTrace(
                trace_field,
                trace,
                window,
                pixmap_dim,
                highlight=True
            )
        return trace_field
    
    