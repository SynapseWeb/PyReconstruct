import math

from PySide6.QtCore import Qt, QPoint, QLine
from PySide6.QtGui import (
    QPixmap,
    QPen,
    QColor,
    QPainter,
    QBrush
)
from modules.pyrecon import (
    Series, 
    Section,
    Trace,
    Ztrace
)
from modules.backend.func import (
    getExterior, 
    mergeTraces, 
    reducePoints, 
    cutTraces
)
from modules.calc import (
    pointInPoly,
    pixmapPointToField,
    fieldPointToPixmap,
    getDistanceFromTrace
)
from modules.gui.utils import notify

class TraceLayer():

    def __init__(self, section : Section, series : Series):
        """Create a trace layer.
        
            Params:
                section (Section): the section object for the layer
                series (Series): the series object
        """
        self.section = section
        self.series = series
        self.traces_in_view = []
        self.zsegments_in_view = []
    
    def pointToPix(self, pt : tuple, apply_tform=True, qpoint=False) -> tuple:
        """Return the pixel point corresponding to a field point.
        
            Params:
                pt (tuple): the trace to convert
                apply_tform (bool): true if section transform should be applied to the point
                qpoints (bool): True if points should be converted QPoint
            Returns:
                (tuple): the pixel point
        """
        x, y = tuple(pt)
        if apply_tform:
            tform = self.section.tforms[self.series.alignment]
            x, y = tform.map(x, y)
        x, y = fieldPointToPixmap(x, y, self.window, self.pixmap_dim, self.section.mag)

        if qpoint:
            new_pt = QPoint(x, y)
        else:
            new_pt = (x, y)
        
        return new_pt
    
    def traceToPix(self, trace : Trace, qpoints=False) -> list:
        """Return the set of pixel points corresponding to a trace.
        
            Params:
                trace (Trace): the trace to convert
                qpoints (bool): True if points should be converted QPoint
            Returns:
                (list): list of pixel points
        """
        new_pts = []
        for point in trace.points:
            new_pts.append(self.pointToPix(point, qpoint=qpoints))
        return new_pts
    
    def getTrace(self, pix_x : float, pix_y : float) -> Trace:
        """"Return the closest trace to the given field coordinates.
        
            Params:
                pix_x (float): the x-coord of the point in the widget
                pix_y (float): the y-coord of the point in the widget
            Returns:
                (Trace): the closest trace
        """
        field_x, field_y = pixmapPointToField(pix_x, pix_y, self.pixmap_dim, self.window, self.section.mag)

        # calculate radius based on window size (2% of window size)
        window_size = max(self.window[2:])
        radius = window_size / 100

        return self.section.findClosestTrace(
            field_x,
            field_y,
            radius=radius,
            traces_in_view=self.traces_in_view
        )
    
    def getTraces(self, pix_poly : list) -> list[Trace]:
        """"Select all traces that are completely in a polygon
        
            Params:
                pix_poly (list): a list of screen points
            Returns:
                (list[Trace]): the list of traces within the polygon
        """
        if len(pix_poly) < 3:
            return
        
        # convert the pix_poly into its exterior
        pix_poly = getExterior(pix_poly)

        traces_in_poly = []
        # only check traces in the view
        for trace in self.traces_in_view:
            pix_points = self.traceToPix(trace)
            inside_poly = True
            # check if EVERY point is inside the polygon
            for point in pix_points:
                if not pointInPoly(*point, pix_poly):
                    inside_poly = False
                    break
            if inside_poly:
                traces_in_poly.append(trace)
        
        ztraces_in_poly = []
        for ztrace in self.series.ztraces.values():
            # check if point is inside polygon
            for i, (x, y, snum) in enumerate(ztrace.points):
                if snum == self.section.n:
                    pix_point = self.pointToPix((x, y))
                    if pointInPoly(*pix_point, pix_poly):
                        ztraces_in_poly.append((ztrace, i))

        return traces_in_poly, ztraces_in_poly

    def getZsegment(self, pix_x : float, pix_y : float, radius = 10):
        """Find the closest ztrace segment (does not have a point on the section).
        
            Params:
                pix_x (float): the screen pixel x
                pix_y (float): the screen pixel y
                radius (float): the max radius for finding a ztrace segment
        """
        if not self.zsegments_in_view:
            return None
        
        closest_dist = None
        closest_ztrace = None
        for line, ztrace in self.zsegments_in_view:
            d = getDistanceFromTrace(
                pix_x,
                pix_y,
                line,
                factor=1,
                absolute=True
            )
            if (d < radius and 
                (closest_dist is None or d < closest_dist)
            ):
                closest_dist = d
                closest_ztrace = ztrace
        
        return closest_ztrace

    def newTrace(self, pix_trace : list, base_trace : Trace, closed=True, log_message=None, origin_traces=None):
        """Create a new trace from pixel coordinates.
        
            Params:
                pix_trace (list): pixel coordinates for the new trace
                base_trace (Trace): the trace containing the desired attributes
                closed (bool): whether or not the new trace is closed
                log_message (str): the log message for the new trace action
                origin_traces (list): the traces that the new trace came from (used in the cases of merging and cutting; keeps track of history)
        """
        if len(pix_trace) < 2:  # do not create a new trace if there is only one point
            return
        if closed:
            pix_trace = getExterior(pix_trace)  # get exterior if closed (will reduce points)
        else:
            pix_trace = reducePoints(pix_trace, closed=False)  # only reduce points if trace is open

        # create the new trace
        new_trace = base_trace.copy()
        new_trace.closed = closed
        new_trace.points = []
        new_trace.history = []
        # merge the history of any origin traces
        if origin_traces:
            for trace in origin_traces:
                new_trace.mergeHistory(trace)

        # get the points
        tform = self.section.tforms[self.series.alignment]
        for point in pix_trace:
            field_point = pixmapPointToField(point[0], point[1], self.pixmap_dim, self.window, self.section.mag)
            rtform_point = tform.map(*field_point, inverted=True) # apply the inverse tform to fix trace to base image
            new_trace.add(rtform_point)
        
        # add the trace to the section and select
        if log_message:
            self.section.addTrace(new_trace, log_message)
        else:
            self.section.addTrace(new_trace)
        self.section.selected_traces.append(new_trace)
    
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
        tform = self.section.tforms[self.series.alignment]
        new_trace = trace.copy()
        new_trace.points = []
        for point in trace.points:
            field_point = (point[0] + field_x, point[1] + field_y)
            rtform_point = tform.map(*field_point, inverted=True)  # fix the coords to image
            new_trace.add(rtform_point)
        self.section.addTrace(new_trace)
        self.section.selected_traces.append(new_trace)
    
    def mergeSelectedTraces(self):
        """Merge all selected traces."""
        if len(self.section.selected_traces) < 2:
            notify("Please select two or more traces to merge.")
            return
        traces = []
        first_trace = self.section.selected_traces[0]
        name = first_trace.name
        for trace in self.section.selected_traces:
            if trace.closed == False:
                notify("Please merge only closed traces.")
                return
            if trace.name != name:
                notify("Please merge traces with the same name.")
                return
            # collect pixel values for trace points
            pix_points = self.traceToPix(trace)
            traces.append(pix_points)
        merged_traces = mergeTraces(traces)  # merge the pixel traces
        # delete the old traces
        origin_traces = self.section.selected_traces.copy()
        self.section.deleteTraces()
        # create new merged trace
        for trace in merged_traces:
            self.newTrace(
                trace,
                first_trace,
                log_message="merged",
                origin_traces=origin_traces
            )
    
    def cutTrace(self, knife_trace : list):
        """Cuts the selected trace along the knife line.
        
            Params:
                knife_trace (list): the knife trace in pixmap points
        """
        trace = self.section.selected_traces[0]
        trace_to_cut = self.traceToPix(trace)
        cut_traces = cutTraces(trace_to_cut, knife_trace)  # merge the pixel traces
        # delete the old traces
        origin_traces = self.section.selected_traces.copy()
        self.section.deleteTraces()
        # create new traces
        for piece in cut_traces:
            # add the trace history to the piece
            self.newTrace(
                piece,
                trace,
                log_message="split with knife",
                origin_traces=origin_traces
            )
    
    def eraseArea(self, pix_x : int, pix_y : int):
        """Erase an area of the field.
        
            Params:
                pix_x (int): the x coord for erasing
                pix_y (int): the y coord for erasing
        """
        trace = self.getTrace(pix_x, pix_y)
        if trace:
            self.section.removeTrace(trace)
            if trace in self.section.selected_traces:
                self.section.selected_traces.remove(trace)
            return True
        return False
    
    def getCopiedTraces(self, cut=False) -> list:
        """Called when user presses Ctrl+C or Ctrl+X.
        
            Params:
                cut (bool): whether or not to delete the traces
            Returns:
                (list): the traces to copy
        """
        copied_traces = []
        for trace in self.section.selected_traces:
            trace = trace.copy()
            tform = self.section.tforms[self.series.alignment]
            trace.points = [tform.map(*p) for p in trace.points]
            copied_traces.append(trace)
        
        if cut:
            self.section.deleteTraces()
        
        return copied_traces
    
    def pasteTraces(self, traces : list[Trace]):
        """Called when the user presses Ctrl+V.
        
            Params:
                traces (list): a list of trace objects to paste
        """
        for trace in traces:
            trace = trace.copy()
            tform = self.section.tforms[self.series.alignment]
            trace.points = [tform.map(*p, inverted=True) for p in trace.points]
            self.section.addTrace(trace, f"copied/pasted")
            self.section.selected_traces.append(trace)
    
    def pasteAttributes(self, traces : list[Trace]):
        """Called when the user pressed Ctrl+B."""
        if len(traces) != 1:
            return
        trace = traces[0]

        name, color, tags, mode = trace.name, trace.color, trace.tags, trace.fill_mode

        self.section.editTraceAttributes(
            traces=self.section.selected_traces,
            name=name,
            color=color,
            tags=tags,
            mode=mode
        )
    
    def _drawTrace(self, trace_layer : QPixmap, trace : Trace) -> bool:
        """Draw a trace on the current trace layer and return bool indicating if trace is in the current view.
        
            Params:
                trace_layer (QPixmap): the pixmap to draw the traces
                trace (Trace): the trace to draw on the pixmap
            Returns:
                (bool) if the trace is within the current field window view
        """        
        # convert to screen coordinates
        qpoints = self.traceToPix(trace, qpoints=True)
        if not qpoints:
            print("EMPTY TRACE DETECTED")
            return

        # get the bounds
        xmin = qpoints[0].x()
        xmax = xmin
        ymin = qpoints[0].y()
        ymax = ymin
        for p in qpoints[1:]:
            x = p.x()
            y = p.y()
            if x < xmin:
                xmin = x
            elif x > xmax:
                xmax = x
            if y < ymin:
                ymin = y
            elif y > ymax:
                ymax = y
        
        trace_bounds = xmin, ymin, xmax, ymax
        screen_bounds = 0, 0, *self.pixmap_dim

        # draw if within view
        if boundsOverlap(trace_bounds, screen_bounds):
            # set up painter
            painter = QPainter(trace_layer)
            painter.setPen(QPen(QColor(*trace.color), 1))

            # draw trace
            if trace.closed:
                painter.drawPolygon(qpoints)
            else:
                painter.drawPolyline(qpoints)
            
            # draw highlight
            if trace in self.section.selected_traces:
                painter.setPen(QPen(QColor(*trace.color), 8))
                painter.setOpacity(0.4)
                if trace.closed:
                    painter.drawPolygon(qpoints)
                else:
                    painter.drawPolyline(qpoints)
            
            # determine if user requested fill
            if (
                (trace.fill_mode[0] != "none") and
                ((trace.fill_mode[1] == "selected") == (trace in self.section.selected_traces))
            ): fill = True
            else: fill = False

            # fill in shape if requested
            if fill:
                painter.setPen(QPen(QColor(*trace.color), 1))
                painter.setBrush(QBrush(QColor(*trace.color)))
                # determine the type of fill
                if trace.fill_mode[0] == "transparent":  # transparent fill
                    painter.setOpacity(self.series.fill_opacity)
                elif trace.fill_mode[0] == "solid":  # solid
                    painter.setOpacity(1)
                painter.drawPolygon(qpoints)
        
            return True

        else:
            return False
    
    def _drawZtrace(self, trace_layer : QPixmap, ztrace : Ztrace):
        """Draw points on the current trace layer.
        
            Params:
                trace_layer (QPixmap): the pixmap to draw the point
                points (list): the list of points to draw
        """
        points, lines = ztrace.getSectionData(self.series, self.section)
        # convert to screen coordinates
        qpoints = []
        for pt in points:
            qpoints.append(self.pointToPix(
                pt,
                apply_tform=False,
                qpoint=True
            ))
        qlines = []
        for p1, p2 in lines:
            qp1 = self.pointToPix(
                p1[:2],
                apply_tform=False,
                qpoint=True
            )
            qp2 = self.pointToPix(
                p2[:2],
                apply_tform=False,
                qpoint=True
            )
            qlines.append(QLine(qp1, qp2))
        
        # set up painter
        painter = QPainter(trace_layer)
        painter.setPen(QPen(QColor(*ztrace.color), 6))

        # draw points and lines
        painter.drawPoints(qpoints)
        painter.setPen(QPen(QColor(*ztrace.color), 1))
        for line in qlines:
            p1 = line.p1()
            p2 = line.p2()
            p1_arrow = True
            p2_arrow = True
            if p1 in qpoints:
                p1_arrow = False
            if p2 in qpoints:
                p2_arrow = False
            drawArrow(
                painter,
                line,
                p1_arrow,
                p2_arrow
            )
            self.zsegments_in_view += [(
                ((p1.x(), p1.y()),
                (p2.x(), p2.y())),
                ztrace
            )]
        painter.end()
    
    def _drawZtraceHighlights(self, trace_layer : QPixmap):
        """Draw highlighted points on the current trace layer.
        
            Params:
                trace_layer (QPixmap): the pixmap to draw the points
        """
        points = []
        colors = []
        for ztrace, i in self.section.selected_ztraces:
            if ztrace not in self.section.temp_hide:
                points.append(ztrace.points[i][:2])
                colors.append(ztrace.color)

        # convert to screen coordinates
        qpoints = []
        for pt in points:
            qpoints.append(self.pointToPix(
                pt,
                qpoint=True
            ))
        
        # set up painter
        painter = QPainter(trace_layer)
        painter.setOpacity(self.series.fill_opacity)

        # draw points
        for qpoint, color in zip(qpoints, colors):
            painter.setPen(QPen(QColor(*color), 15))
            painter.drawPoint(qpoint)
        painter.end()
   
    def generateTraceLayer(self, pixmap_dim : tuple, window : list, show_all_traces=False, window_moved=True) -> QPixmap:
        """Generate the traces on a transparent background.
        
            Params:
                pixmap_dim (tuple): the w and h of the pixmap to be output
                window (list): the view of the window (x, y, w, h)
                show_all_traces (bool): True if all traces are displayed regardless of hidden status
                window_moved (bool): True if the window has moved (upstream: same as generate_image)
            Returns:
                (QPixmap): the pixmap with traces drawn in
        """
        self.window = window
        self.pixmap_dim = pixmap_dim
        pixmap_w, pixmap_h = tuple(pixmap_dim)
        trace_layer = QPixmap(pixmap_w, pixmap_h)
        trace_layer.fill(Qt.transparent)

        if window_moved:
            trace_list = self.section.tracesAsList()
        else:
            trace_found = False
            for trace in self.section.removed_traces:
                for view_trace in self.traces_in_view:
                    if trace.isSameTrace(view_trace):
                        trace_found = True
                        break
                if trace_found:
                    self.traces_in_view.remove(view_trace)
            for trace in self.section.added_traces:
                self.traces_in_view.append(trace)
            trace_list = self.traces_in_view.copy()
        
        self.traces_in_view = []
        for trace in trace_list:
            if (
                trace not in self.section.temp_hide and
                (show_all_traces or not trace.hidden)
            ):
                trace_in_view = self._drawTrace(
                    trace_layer,
                    trace
                )
                if trace_in_view:
                    self.traces_in_view.append(trace)
        
        # draw ztraces
        self.zsegments_in_view = []
        if self.series.options["show_ztraces"]:
            for ztrace in self.series.ztraces.values():
                if ztrace not in self.section.temp_hide:
                    self._drawZtrace(trace_layer, ztrace)
        self._drawZtraceHighlights(trace_layer)
                
        return trace_layer


def boundsOverlap(b1 : tuple, b2 : tuple):
    """Check if two bounding boxes intersect.
    
        Params:
            b1 (tuple): xmin, ymin, xmax, ymax
            b2 (tuple): xmin, ymin, xmax, ymax
        Returns:
            (bool): True if bounds have any overlap
    """

    return not (
        b1[2] < b2[0] or 
        b1[0] > b2[2] or 
        b1[3] < b2[1] or 
        b1[1] > b2[3]
    )

def boundsOverlap(b1 : tuple, b2 : tuple):
    """Check if two bounding boxes intersect.
    
        Params:
            b1 (tuple): xmin, ymin, xmax, ymax
            b2 (tuple): xmin, ymin, xmax, ymax
        Returns:
            (bool): True if bounds have any overlap
    """

    return not (
        b1[2] < b2[0] or 
        b1[0] > b2[2] or 
        b1[3] < b2[1] or 
        b1[1] > b2[3]
    )

def getTheta(line : QLine):
    """Get the angle a line makes with the x-axis.
    
        Params:
            line (QLine): the qline to get the angle for
    """
    p1 = line.p1()
    p2 = line.p2()
    v = p2 - p1
    if v.x() == 0:
        if v.y() < 0:
            theta = 3*math.pi/2
        elif v.y() > 0:
            theta = math.pi/2
        else:
            theta = None
    elif v.x() < 0:
        theta = math.pi + math.atan(v.y()/v.x())
    elif v.x() > 0:
        theta = math.atan(v.y()/v.x())
    
    return theta
    
def drawArrowHead(painter : QPainter, pt : QPoint, theta : float, l = 5):
    """Draw an arrowhead in a given direction.
    
        Params:
            painter (QPainter): the painter to draw the arrowhead
            pt (QPoint): the point on which the arrowhead is located
            theta (float): the angle (in radians) of the arrowhead (cc from x-axis)
            l (int): the length of the arrowhead
    """
    theta += math.pi
    t1 = theta + math.pi/6
    t2 = theta - math.pi/6
    p1 = QPoint(
        pt.x() + l * math.cos(t1),
        pt.y() + l * math.sin(t1)
    )
    p2 = pt
    p3 = QPoint(
        pt.x() + l * math.cos(t2),
        pt.y() + l * math.sin(t2)
    )
    l1 = QLine(p1, p2)
    l2 = QLine(p2, p3)
    painter.drawLine(l1)
    painter.drawLine(l2)

def drawArrow(painter : QPainter, line : QLine, p1_arrow=True, p2_arrow=True):
    """Draw an line with one or two arrowheads.
    
        Params:
            painter (QPainter): the painter used to draw the arrow
            line (QLine): the ztrace qline
            p1_arrow (bool): True if arrowhead on the first point
            p2_arrow (bool): True if arrowhead on the second point
    """
    painter.drawLine(line)
    theta = getTheta(line)
    if theta is not None:
        if p1_arrow:
            drawArrowHead(painter, line.p1(), theta)
        if p2_arrow:
            drawArrowHead(painter, line.p2(), theta)

        
