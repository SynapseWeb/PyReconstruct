from quantification import area

CC_TO_VECTOR = ((1,0), (1,1), (0,1), (-1,1), (-1,0), (-1,-1), (0,-1), (1,-1))  

class Grid():

    def __init__(self, contours, cutline=None):
        """Create a grid object."""
        self.contours = contours  # list of traces (pixel coordinates)
        self.cutline = cutline  # scalpel line (not implemented yet)
        self.grid = []
        self._generateGrid()
    
    def _generateGrid(self):
        """Draw all the contours on the grid."""
        self.grid = []  # clear existing grid
        xmin, ymin, xmax, ymax = self._getMinMaxXY()
        # create an empty grid
        for i in range(ymax - ymin + 1):
            self.grid.append([])
            for j in range(xmax - xmin + 1):
                self.grid[i].append(0)
        # draw the trace on the grid
        for i in range(len(self.contours)):
            contour = self.contours[i]
            for j in range(len(contour)):
                x1, y1 = contour[j-1]
                x2, y2 = contour[j]
                x1 -= xmin
                y1 -= ymin
                x2 -= xmin
                y2 -= ymin
                self._drawGridLine(x1, y1, x2, y2)
        # save grid information
        self.grid_h = len(self.grid)
        self.grid_w = len(self.grid[0])
        self.grid_shift = xmin, ymin
    
    def _getMinMaxXY(self) -> tuple:
        """Get the min and max coordinate values for all contours
        
            Returns:
                (float) min x value
                (float) min y value
                (float) max x value
                (float) max y value
        """
        xmin = self.contours[0][0][0]
        ymin = self.contours[0][0][1]
        xmax = self.contours[0][0][0]
        ymax = self.contours[0][0][1]
        for contour in self.contours:
            for point in contour:
                if point[0] < xmin:
                    xmin = point[0]
                elif point[0] > xmax:
                    xmax = point[0]
                if point[1] < ymin:
                    ymin = point[1]
                elif point[1] > ymax:
                    ymax = point[1]
        return xmin, ymin, xmax, ymax
    
    # DDA algorithm (source: https://www.tutorialspoint.com/computer_graphics/line_generation_algorithm.htm)
    def _drawGridLine(self, x0 : int, y0 : int, x1 : int, y1 : int):
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
        self.grid[y][x] += 1
        last_x, last_y = x, y
        for i in range(steps):
            x += x_increment
            y += y_increment
            rx = round(x)
            ry = round(y)
            if (rx != last_x or ry != last_y):
                self.grid[ry][rx] += 1
                last_x, last_y = rx, ry
    
    def _drawCutLine(self, x0 : int, y0 : int, x1 : int, y1 : int):
        """Draw a scalpel line on the grid (not used yet)
        
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
        # draw scalpel lines as negative numbers
        if 0 <= x < len(self.grid[0]) and 0 <= y < len(self.grid):
            if self.grid[rx][ry] <= 0:
                self.grid[ry][rx] -= 1
            else:
                self.grid[ry][rx] = -self.grid[ry][rx] - 1
        last_x, last_y = x, y
        for i in range(steps):
            x += x_increment
            y += y_increment
            rx = round(x)
            ry = round(y)
            if (rx != last_x or ry != last_y) and 0 <= rx < len(self.grid[0]) and 0 <= ry < len(self.grid):
                if self.grid[rx][ry] <= 0:
                    self.grid[ry][rx] -= 1
                else:
                    self.grid[ry][rx] = -self.grid[ry][rx] - 1
                last_x, last_y = rx, ry
    
    def printGrid(self):
        """Print the grid to the console.
        
        Mostly for debugging purposes.
        """
        for r in range(len(self.grid)):
            for c in range(len(self.grid[r])):
                if self.grid[r][c]: print(self.grid[r][c], end="")
                else: print(" ", end="")
            print()
    
    def _checkSurrounding(self, x : int, y : int):
        """Find the number of occupied spaces around a given point.
        
            Params:
                x (int): x-value of point
                y (int) y-value of point
            Returns:
                (int) the number of occupied (non-zero) spaces around the point
                """
        count = 0
        for i in range(8):
            v = CC_TO_VECTOR[i]
            x1 = x + v[0]
            y1 = y + v[1]
            if x1 < 0 or x1 >= len(self.grid[0]):
                continue
            if y1 < 0 or y1 >= len(self.grid):
                continue
            if self.grid[y + v[1]][x + v[0]] > 0:
                count += 1
        return count
    
    def _deleteContour(self, x : int, y : int):
        """Delete the contour on the grid at a given point.
        
            Params:
                x (int): x-value of point on contour
                y (int) y-value of point on contour
        """
        # use a stack instead of recursion
        stack = [(x,y)]
        while stack:
            x1, y1 = stack.pop()
            if self.grid[y1][x1]:
                self.grid[y1][x1] = 0
                for i in range(8):
                    v = CC_TO_VECTOR[i]
                    x2 = x1 + v[0]
                    y2 = y1 + v[1]
                    if 0 <= x2 < self.grid_w and 0 <= y2 < self.grid_h:
                        stack.append((x2,y2))
    
    def generateExterior(self, x=0, y=0, delete=False) -> list:
        """Get the exterior of the contour(s) on the grid.
        
            Params:
                x (int): x-value of point on contour
                y (int): y-value of pointon contour
                delete (bool): whether or not to delete the contour when finished
            Returns:
                (list) the exterior of the contour(s)
        """
        exterior = []
        # search the grid until a contour is found
        x1, y1 = x, y
        xshift = self.grid_shift[0]
        yshift = self.grid_shift[1]
        while not self.grid[y1][x1]:
            x1 += 1
            if x1 == self.grid_w:
                x1 = 0
                y1 += 1
                if y1 == self.grid_h:
                    return
        exterior_origin = (x1, y1)  # save contour location

        # check points: add to contour if there is a point, intersection, or cluster of lines
        if self.grid[y1][x1] > 1 or self._checkSurrounding(x1, y1) >= 4:  # cehck first point
            exterior.append((x1 + xshift, y1 + yshift))
        for c in range(8):  # find the next point
            v = CC_TO_VECTOR[c]
            x2 = x1 + v[0]
            y2 = y1 + v[1]
            if 0 <= x2 < self.grid_w and 0 <= y2 < self.grid_h:
                if self.grid[y2][x2]:
                    x1 = x2
                    y1 = y2
                    last_c = c
                    break
        if self.grid[y1][x1] > 1 or self._checkSurrounding(x1, y1) >= 4:  # check next point
            exterior.append((x1 + xshift, y1 + yshift))
        # begin traveling around the contour
        while (x1, y1) != exterior_origin:
            last_c = (last_c + 4) % 8  # invert the last chain code direction
            for i in range(1, 8):
                c = (last_c + i) % 8  # search for the next point starting from the outside
                v = CC_TO_VECTOR[c]
                x2 = x1 + v[0]
                y2 = y1 + v[1]
                if 0 <= x2 < self.grid_w and 0 <= y2 < self.grid_h:
                    if self.grid[y2][x2]:
                        x1 = x2
                        y1 = y2
                        last_c = c
                        if self.grid[y1][x1] > 1 or self._checkSurrounding(x1, y1) >= 4:
                            exterior.append((x1 + xshift, y1 + yshift))
                        break
        # delete the contour if requested
        if delete:
            self._deleteContour(x1, y1)
        
        return exterior

def reducePoints(points : list) -> list:
    """Remove points the do not contribute further information to a contour.
    
        Params:
            points (list): list of points describing contour
        Returns:
            (list) reduced points
    """
    reduced_points = points.copy()
    i = 1
    while i < len(reduced_points) - 1:
        a = area((reduced_points[i-1], reduced_points[i], reduced_points[i+1]))
        if a <= 1.5: # remove point from contour if affect on trace is insignificant
            reduced_points.pop(i)
        else:
            i += 1
    return reduced_points

def getExterior(points : list):
    """Get the exterior of a single set of points.
    
        Params:
            points (list): points describing the contour
        Returns:
            (list) points describing contour exterior
    """
    grid = Grid([points])
    new_points = grid.generateExterior()
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
    new_traces = []
    grid_has_traces = True
    while grid_has_traces:
        new_points = grid.generateExterior(delete=True)
        if new_points is None:
            grid_has_traces = False
        else:
            new_traces.append(new_points)
    if len(new_traces) == len(trace_list):
        return trace_list
    return new_traces

