import math

CC_TO_VECTOR = ((1,0), (1,1), (0,1), (-1,1), (-1,0), (-1,-1), (0,-1), (1,-1))  

class Grid():

    def __init__(self, contours, cutline=None):
        self.contours = contours
        self.cutline = cutline
        self.grid = []
        self._generateGrid()
    
    def printGrid(self):
        for r in range(len(self.grid)):
            for c in range(len(self.grid[r])):
                if self.grid[r][c]: print(self.grid[r][c], end="")
                else: print(" ", end="")
            print()
    
    # DDA algorithm (source: https://www.tutorialspoint.com/computer_graphics/line_generation_algorithm.htm)
    def _drawGridLine(self, x0, y0, x1, y1):
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
    
    def _drawCutLine(self, x0, y0, x1, y1):
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
        if 0 <= x < len(self.grid[0]) and 0 <= y < len(self.grid):
            self.grid[y][x] += 1
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

    def _getMinMaxXY(self):
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
    
    def _generateGrid(self):
        self.grid = []
        xmin, ymin, xmax, ymax = self._getMinMaxXY()
        for i in range(ymax - ymin + 1):
            self.grid.append([])
            for j in range(xmax - xmin + 1):
                self.grid[i].append(0)
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
        self.grid_h = len(self.grid)
        self.grid_w = len(self.grid[0])
        self.grid_shift = xmin, ymin
    
    def _checkSurrounding(self, x, y):
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
    
    def generateExterior(self, x=0, y=0, delete=False):
        exterior = []
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
        exterior_origin = (x1, y1)
        if self.grid[y1][x1] > 1 or self._checkSurrounding(x1, y1) >= 4:
            exterior.append((x1 + xshift, y1 + yshift))
        for c in range(8):
            v = CC_TO_VECTOR[c]
            x2 = x1 + v[0]
            y2 = y1 + v[1]
            if 0 <= x2 < self.grid_w and 0 <= y2 < self.grid_h:
                if self.grid[y2][x2]:
                    x1 = x2
                    y1 = y2
                    last_c = c
                    break
        if self.grid[y1][x1] > 1 or self._checkSurrounding(x1, y1) >= 4:
            exterior.append((x1 + xshift, y1 + yshift))
        while (x1, y1) != exterior_origin:
            last_c = (last_c + 5) % 8
            for i in range(7):
                c = (last_c + i) % 8
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
        if delete:
            self._deleteContour(x1, y1)
        
        return exterior

    def _deleteContour(self, x, y):
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

def polygonArea(vertices):
    if len(vertices) == 2:
        return 0

    psum = 0
    nsum = 0

    for i in range(len(vertices)):
        sindex = (i + 1) % len(vertices)
        prod = vertices[i][0] * vertices[sindex][1]
        psum += prod

    for i in range(len(vertices)):
        sindex = (i + 1) % len(vertices)
        prod = vertices[sindex][0] * vertices[i][1]
        nsum += prod

    return abs(1/2*(psum - nsum))

def reducePoints(points):
    reduced_points = points.copy()
    i = 1
    while i < len(reduced_points) - 1:
        area = polygonArea((reduced_points[i-1], reduced_points[i], reduced_points[i+1]))
        if area <= 1:
            reduced_points.pop(i)
        else:
            i += 1
    return reduced_points

def getExterior(points):
    grid = Grid([points])
    new_points = grid.generateExterior()
    new_points = reducePoints(new_points)
    return new_points

def mergeTraces(trace_list):
    grid = Grid(trace_list)
    #grid.printGrid()
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

