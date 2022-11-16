import numpy as np
import cv2

from modules.calc.quantification import area

class Grid():

    def __init__(self, contours, cutline=None):
        """Create a grid object."""
        self.contours = [np.array(contour) for contour in contours]
        self.cutline = cutline  # knife line
        self._generateGrid()
    
    def _generateGrid(self):
        """Draw all the contours on the grid."""
        xvals = [contour[:,0] for contour in self.contours]
        yvals = [contour[:,1] for contour in self.contours]
        xmin = min([x.min() for x in xvals])
        ymin = min([y.min() for y in yvals])
        xmax = max([x.max() for x in xvals])
        ymax = max([y.max() for y in yvals])
        # create an empty grid
        self.grid = np.array(np.zeros((ymax-ymin+2, xmax-xmin+2)), dtype="int")
        # draw cut line on the grid
        if self.cutline is not None:
            for i in range(1, len(self.cutline)):
                x1, y1 = self.cutline[i-1]
                x2, y2 = self.cutline[i]
                x1 -= xmin
                y1 -= ymin
                x2 -= xmin
                y2 -= ymin
                self._drawGridLine(x1, y1, x2, y2, knife=True)
        # draw the trace(s) on the grid
        for contour in self.contours:
            for i in range(len(contour)):
                x1, y1 = contour[i-1]
                x2, y2 = contour[i]
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
                self.grid[y, x] -= 1
            else:
                self.grid[y, x] = abs(self.grid[y, x]) + 1
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
        """Turn grid cuts into normal lines."""
        y_vals, x_vals = np.where(self.grid < 0) # get positions of negative numbers (cut line)
        for x, y in zip(x_vals, y_vals):
            inside = False
            # check if the point is inside any of the contours
            for contour in self.contours:
                ptest = cv2.pointPolygonTest(contour,
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
        
        Mostly for debugging purposes.
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

    def getAnchorContour(self, contour : np.ndarray) -> np.ndarray:
        """Get the "anchor" contour from a numpy cv2 contour.
        
        Often run after cv2.findContours is run on the grid.
        
            Params:
                contour (np.ndarray): the contour returned by cv2.findContours
            Returns:
                (np.ndarray) the anchor points of the contour
        """
        new_contour = []
        for point in contour:
            if self.isAnchorPoint(*point):
                new_contour.append(point)
        return np.array(new_contour)
    
    def getExterior(self) -> list:
        """Get the exterior of the contour(s) on the grid.
        
            Returns:
                (list) the exterior of the contour(s) (also represented as lists)
        """
        cv_contours, hierarchy = cv2.findContours(self.grid.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        contours = []
        for contour in cv_contours:
            new_contour = self.getAnchorContour(contour[:,0,:])
            new_contour += self.grid_shift
            contours.append(new_contour.tolist())
        return contours

    def getInteriors(self) -> list:
        """Get the interiors of the contours on the grid.
        
            Returns:
                (list) the interiors of the contours (also represented as lists)
        """
        self.removeCuts()
        cv_contours, hierarchy = cv2.findContours(self.grid.astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        contours = []
        for contour in cv_contours[:-1]:
            new_contour = self.getAnchorContour(contour[:,0,:])
            new_contour += self.grid_shift
            contours.append(new_contour.tolist())
        return contours

def reducePoints(points : list, ep=0.80, iterations=1, closed=True, mag=None) -> list:
    """Reduce the number of points in a trace (uses cv2.approxPolyDP).
    
        Params:
            points (list): the list of points in the contour
            ep (float): the epsilon value for the approximation
            iterations (int): the number of times the approximation is run
            closed (bool): whether or not the trace is closed
            mag (float): magnifcation for the trace
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
    
    return reduced_points[:,0,:].tolist()


def getExterior(points : list) -> list:
    """Get the exterior of a single set of points.
    
        Params:
            points (list): points describing the contour
        Returns:
            (list) points describing contour exterior
    """
    grid = Grid([points])
    new_points = grid.getExterior()[0]
    new_points = reducePoints(new_points)
    return new_points

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

def cutTraces(trace, cut_trace : list) -> list:
    """Cut a set of traces.
    
        Params:
            trace_list (list): set of traces
            cut_line (list): a single curve
        Returns:
            (list) the newly cut traces
    """
    threshold = area(trace) * 0.01
    grid = Grid([trace], cut_trace)
    interiors = grid.getInteriors()
    new_traces = []
    for i in range(len(interiors)):
        if area(interiors[i]) >= threshold: # exclude traces that are smaller than 1% of the original trace area
            new_traces.append(reducePoints(interiors[i]))

    return new_traces
        

