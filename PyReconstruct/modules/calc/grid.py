import cv2
import numpy as np

from .quantification import area, lineDistance

class Grid():

    def __init__(self, traces, cutline=None):
        """Create a grid object.
        
            Params:
                traces (list): a list of traces, each one being a list of points
                cutline (list): a list of points created by the knife tool
        """
        self.traces = [np.array(trace) for trace in traces]
        self.cutline = cutline  # knife line
        self._generateGrid()
    
    def _generateGrid(self):
        """Draw all the traces on the grid."""
        # get the boundaries of the trace
        xvals = [trace[:,0] for trace in self.traces]
        yvals = [trace[:,1] for trace in self.traces]
        xmin = min([x.min() for x in xvals])
        ymin = min([y.min() for y in yvals])
        xmax = max([x.max() for x in xvals])
        ymax = max([y.max() for y in yvals])

        # create an empty grid
        self.grid = np.array(
            np.zeros((ymax-ymin+2, xmax-xmin+2)),
            dtype="int"
        )

        # draw knife line on grid if applicable
        if self.cutline is not None:
            for i in range(1, len(self.cutline)):
                x1, y1 = self.cutline[i-1]
                x2, y2 = self.cutline[i]
                x1 -= xmin
                y1 -= ymin
                x2 -= xmin
                y2 -= ymin
                self._drawGridLine(x1, y1, x2, y2, knife=True)
        
        # draw the trace(s) on the grid (ASSUMES CLOSED)
        for trace in self.traces:
            for i in range(len(trace)):
                x1, y1 = trace[i-1]
                x2, y2 = trace[i]
                x1 -= xmin
                y1 -= ymin
                x2 -= xmin
                y2 -= ymin
                self._drawGridLine(x1, y1, x2, y2)
        
        # save grid information
        self.grid_shift = xmin, ymin
    
    # DDA algorithm
    # Source: https://www.tutorialspoint.com/computer_graphics/line_generation_algorithm.htm
    def _drawGridLine(self, x0 : int, y0 : int, x1 : int, y1 : int, knife=False):
        """Draw a line on self.grid.
        
            Params:
                x0 (int): x value of start point
                y0 (int): y value of start point
                x1 (int): x value of end point
                y1 (int): y value of end point
                knife (bool): True if the trace is a knife trace
        """
        if (x0 == x1 and y0 == y1):
            return
        dx = x1 - x0
        dy = y1 - y0
        if (abs(dx) > abs(dy)):
            steps = abs(dx)
        else:
            steps = abs(dy)    
        x_increment = dx / steps
        y_increment = dy / steps
        x, y = x0, y0
        h, w = self.grid.shape
        if 0 <= x < w and 0 <= y < h:
            if knife:
                self.grid[y, x] -= 1  # knife traces are negative
            else:
                self.grid[y, x] = abs(self.grid[y, x]) + 1  # traces are positive
        last_x, last_y = x, y
        for _ in range(steps):
            x += x_increment
            y += y_increment
            rx = round(x)
            ry = round(y)
            if (rx != last_x or ry != last_y):
                if 0 <= rx < w and 0 <= ry < h:
                    if knife:
                        self.grid[ry, rx] -= 1
                    else:
                        self.grid[ry, rx] = abs(self.grid[ry, rx]) + 1
                last_x, last_y = rx, ry

    def removeCuts(self):
        """Turn grid cuts into normal lines.
        
        Negative values within the shape are made positive.
        """
        y_vals, x_vals = np.where(self.grid < 0) # get positions of negative numbers (cut line)
        for x, y in zip(x_vals, y_vals):
            inside = False
            # check if the point is inside any of the traces
            for trace in self.traces:
                ptest = cv2.pointPolygonTest(trace,
                                        (int(x + self.grid_shift[0]), int(y + self.grid_shift[1])),
                                        measureDist=False)
                if ptest >= 0:
                    inside = True
            if not inside: # if cut is not within any trace, remove it
                self.grid[y, x] = 0
            else: # otherwise, make it part of the trace
                self.grid[y, x] *= -1

    def printGrid(self):
        """Print the grid to the console.
        
        For debugging purposes.
        """
        for r in range(len(self.grid)):
            for c in range(len(self.grid[r])):
                if self.grid[r,c]: print(self.grid[r,c], end="")
                else: print(" ", end="")
            print()
    
    def isAnchorPoint(self, x : int, y : int) -> bool:
        """Check if a grid point should be included in the final trace points.
        
            Params:
                x (int): the x-coord of the point to check
                y (int): the y-coord of the point to check
            Returns:
                (bool) whether or not the point is important to the trace
        """
        if self.grid[y, x] > 1: # point is automatically included if it is greater than 1
            return True
        else: # otherwise, check surrounding points
            cc_list = [(1,0), (1,1), (0,1), (-1,1), (-1,0), (-1,-1), (0,-1), (1,-1)]
            total = 0
            for dx, dy in cc_list:
                if self.grid[y + dy, x + dx] > 0:
                    total += 1
            if total >= 3: # if the point as three or more nonzero neighbors, include it
                return True
            else:
                return False

    def getAnchorTrace(self, trace : np.ndarray) -> np.ndarray:
        """Get the "anchor" trace from a numpy cv2 trace.
        
        Often run after cv2.findContours is run on the grid.
        
            Params:
                trace (np.ndarray): the trace returned by cv2.findContours
            Returns:
                (np.ndarray) the anchor points of the trace
        """
        new_trace = []
        for point in trace:
            if self.isAnchorPoint(*point):
                new_trace.append(point)
        return np.array(new_trace)
    
    def getExterior(self) -> list:
        """Get the exterior of the trace(s) on the grid.
        
            Returns:
                (list) the exterior of the trace(s) (also represented as lists)
        """

        cv_traces, hierarchy = cv2.findContours(
            self.grid.astype(np.uint8),
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_NONE
        )
        
        traces = []
        
        for trace in cv_traces:
            new_trace = self.getAnchorTrace(trace[:,0,:])
            new_trace += self.grid_shift
            traces.append(new_trace.tolist())
            
        return traces

    def getInteriors(self) -> list:
        """Get the interiors of the traces on the grid.
        
            Returns:
                (list) the interiors of the traces (also represented as lists)
        """
        self.removeCuts()
        cv_traces, hierarchy = cv2.findContours(self.grid.astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        traces = []
        for trace in cv_traces[:-1]:
            new_trace = self.getAnchorTrace(trace[:,0,:])
            new_trace += self.grid_shift
            traces.append(new_trace.tolist())
        return traces


# METHODS (used to access the class functions)

def reducePoints(points : list, ep=0.80, iterations=1, closed=True, mag=None, array=False) -> list:
    """Reduce the number of points in a trace (uses cv2.approxPolyDP).
    
        Params:
            points (list): the list of points in the trace
            ep (float): the epsilon value for the approximation
            iterations (int): the number of times the approximation is run
            closed (bool): whether or not the trace is closed
            mag (float): magnifcation for the trace
            array (bool): True if returns as np.ndarray
        Returns:
            (list) the final points after the approximation
    """
    np_pts = np.array(points)
    if mag:
        np_pts *= mag
        np_pts = np_pts.astype(np.int32)

    for _ in range(iterations):
        reduced_points = cv2.approxPolyDP(np_pts, ep, closed=closed)
        # print(len(reduced_points) / len(points))
    
    if mag:
        reduced_points = reduced_points.astype(np.float64)
        reduced_points /= mag
    
    if array:
        return reduced_points[:,0,:]
    else:
        return reduced_points[:,0,:].tolist()

def getExterior(points : list) -> list:
    """Get the exterior of a single set of points.
    
        Params:
            points (list): points describing the trace
        Returns:
            (list) points describing trace exterior
    """
    grid = Grid([points])
    exteriors = grid.getExterior()
    if exteriors:
        new_points = grid.getExterior()[0]
        new_points = reducePoints(new_points)
        return new_points
    else:
        return []

def mergeTraces(trace_list : list) -> list:
    """Get the exterior(s) of a set of traces.
    
        Params:
            trace_list (list): set of traces
        Returns:
            (list) merged set of traces
    """
    grid = Grid(trace_list)
    new_traces = grid.getExterior()
    for i in range(len(new_traces)):
        new_traces[i] = reducePoints(new_traces[i])
    return new_traces

def cutTraces(trace_list, cut_trace : list, del_threshold : float, closed=True) -> list:
    """Cut a set of traces.
    
        Params:
            trace_list (list): set of traces
            cut_line (list): a single curve
        Returns:
            (list) the newly cut traces
    """
    if closed:
        threshold = sum(area(t) for t in trace_list) * (del_threshold / 100)
        grid = Grid(trace_list, cut_trace)
        interiors = grid.getInteriors()
        new_traces = []
        for i in range(len(interiors)):
            if area(interiors[i]) >= threshold: # exclude traces that are smaller than 1% of the original trace area
                new_traces.append(reducePoints(interiors[i]))
    else:
        new_traces = []
        for trace in trace_list:
            threshold = lineDistance(trace, closed=False) * (del_threshold / 100)
            new_traces += cutOpenTrace(trace, cut_trace)
        for t in new_traces.copy():
            if lineDistance(t, closed=False) < threshold:
                new_traces.remove(t)
    
    return new_traces

# Function to check if two line segments intersect
def intersection(line1, line2):
    (x1, y1), (x2, y2) = tuple(line1)
    (x3, y3), (x4, y4) = tuple(line2)

    # Calculate the slopes of the lines
    m1 = (y2 - y1) / (x2 - x1) if x2 - x1 != 0 else float('inf')
    m2 = (y4 - y3) / (x4 - x3) if x4 - x3 != 0 else float('inf')

    # Check if the lines are parallel
    if m1 == m2:
        return None  # The lines do not intersect

    # Calculate the intersection point
    if m1 == float('inf'):  # Line1 is vertical
        x_intersection = x1
        y_intersection = m2 * (x1 - x3) + y3
    elif m2 == float('inf'):  # Line2 is vertical
        x_intersection = x3
        y_intersection = m1 * (x3 - x1) + y1
    else:
        x_intersection = (m1 * x1 - y1 - m2 * x3 + y3) / (m1 - m2)
        y_intersection = m1 * (x_intersection - x1) + y1

    # Check if the intersection point is within the line segments
    if (
        min(x1, x2) <= x_intersection <= max(x1, x2)
        and min(x3, x4) <= x_intersection <= max(x3, x4)
        and min(y1, y2) <= y_intersection <= max(y1, y2)
        and min(y3, y4) <= y_intersection <= max(y3, y4)
    ):
        return (x_intersection, y_intersection)
    else:
        return None  # The lines do not intersect within the line segments

def cutOpenTrace(trace : list, cut_trace : list):
    """Cut an open trace.
    
        Params:
            trace (list): the trace to cut
            cut_trace (list): the trace used to cut
    """
    # insert interect points into trace
    new_trace = []
    cut_indexes = []
    for i in range(len(trace) - 1):
        new_trace.append(trace[i])
        for j in range(len(cut_trace) - 1):
            line1 = [trace[i], trace[i+1]]
            line2 = [cut_trace[j], cut_trace[j+1]]
            pt = intersection(line1, line2)
            if pt:
                cut_indexes.append(len(new_trace))
                new_trace.append(pt)
    new_trace.append(trace[-1])
    
    # split up the trace
    last_i = 0
    traces = []
    for i in cut_indexes:
        traces.append(new_trace[last_i : i+1])
        last_i = i
    traces.append(new_trace[last_i:])

    return traces
        

