import numpy as np
import cv2

from quantification import area

class Grid():

    def __init__(self, contours, cutline=None):
        """Create a grid object."""
        self.contours = [np.array(contour) for contour in contours]
        self.cutline = cutline  # scalpel line
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
        self.grid = np.array(np.zeros((ymax-ymin+2, xmax-xmin+2)), dtype="uint8")
        # draw cut line on the grid
        if self.cutline is not None:
            for i in range(1, len(self.cutline)):
                x1, y1 = self.cutline[i-1]
                x2, y2 = self.cutline[i]
                x1 -= xmin
                y1 -= ymin
                x2 -= xmin
                y2 -= ymin
                self._drawGridLine(x1, y1, x2, y2, scalpel=True)
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
    
    # DDA algorithm (source: https://www.tutorialspoint.com/computer_graphics/line_generation_algorithm.htm)
    def _drawGridLine(self, x0 : int, y0 : int, x1 : int, y1 : int, scalpel=False):
        """Draw a line on self.grid
        
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
            self.grid[y,x] = 2 if scalpel else 1
        last_x, last_y = x, y
        for _ in range(steps):
            x += x_increment
            y += y_increment
            rx = round(x)
            ry = round(y)
            if (rx != last_x or ry != last_y):
                if 0 <= rx < w and 0 <= ry < h:
                    self.grid[ry,rx] = 2 if scalpel else 1
                last_x, last_y = rx, ry
    
    def removeHangingCuts(self):
        h, w = self.grid.shape
        stack = [(w-1, h-1)]
        while len(stack) > 0:
            x, y = stack.pop()
            if 0 <= x < w and 0 <= y < h:
                p = self.grid[y,x]
                if not (p == 1 or p == 3):
                    self.grid[y,x] = 3
                    stack.append((x+1, y))
                    stack.append((x, y+1))
                    stack.append((x-1, y))
                    stack.append((x, y-1))
        self.grid[self.grid == 3] = 0
        self.grid[self.grid == 2] = 1
    
    def printGrid(self):
        """Print the grid to the console.
        
        Mostly for debugging purposes.
        """
        for r in range(len(self.grid)):
            for c in range(len(self.grid[r])):
                if self.grid[r,c]: print(self.grid[r,c], end="")
                else: print(" ", end="")
            print()
    
    def getExterior(self):
        """Get the exterior of the contour(s) on the grid.
        
            Returns:
                (list) the exterior of the contour(s)
        """
        cv_contours = cv2.findContours(self.grid, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0]
        contours = []
        for contour in cv_contours:
            contours.append((contour[:,0,:] + self.grid_shift).tolist())
        return contours

    def getInteriors(self):
        """Get the interiors of the contours on the grid.
        
            Returns:
                (list) the interiors of the contours
        """
        #self.removeHangingCuts()
        cv_contours, hierarchy = cv2.findContours(self.grid, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        contours = []
        for contour in cv_contours[:-1]:
            contours.append((contour[:,0,:] + self.grid_shift).tolist())
        return contours


def reducePoints(points : list, threshold=1, iterations=2) -> list:
    """Remove points the do not contribute further information to a contour.
    
        Params:
            points (list): list of points describing contour
            iterations (int): number of times to implement algorithm
        Returns:
            (list) reduced points
    """
    points = points.copy()
    for _ in range(iterations):
        reduced_points = points.copy()
        i = 1
        while i < len(reduced_points) - 1:
            a = area((reduced_points[i-1], reduced_points[i], reduced_points[i+1]))
            if a <= threshold: # remove point from contour if affect on trace is insignificant
                reduced_points.pop(i)
            else:
                i += 1
        #print(len(reduced_points)/len(points))
        points = reduced_points
    return reduced_points

def getExterior(points : list):
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

def mergeTraces(trace_list : list):
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

def cutTraces(trace, cut_trace : list):
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

