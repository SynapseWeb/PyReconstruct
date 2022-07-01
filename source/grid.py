CC_TO_VECTOR = ((1,0), (1,1), (0,1), (-1,1), (-1,0), (-1,-1), (0,-1), (1,-1))  

class Grid():

    def __init__(self, points=None):
        self.contours = []
        self.grid = []
        if points:
            self.addClosedContour(points)
    
    def addClosedContour(self, points):
        self.contours.append(points)
    
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
    
    def generateGrid(self):
        self.grid = []
        xmin, ymin, xmax, ymax = self._getMinMaxXY()
        for i in range(ymax - ymin + 1):
            self.grid.append([])
            for j in range(xmax - xmin + 1):
                self.grid[i].append(0)
        for i in range(len(self.contours)):
            contour = self.contours[i]
            prev_point = contour[-1]
            for j in range(len(contour)):
                x1, y1 = prev_point
                x2, y2 = contour[j]
                x1 -= xmin
                y1 -= ymin
                x2 -= xmin
                y2 -= ymin
                self._drawGridLine(x1, y1, x2, y2)
                prev_point = contour[j]
        self.grid_h = len(self.grid)
        self.grid_w = len(self.grid[0])
        self.grid_shift = xmin, ymin

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

        x = x0
        y = y0
        self.grid[y][x] = 1
        for i in range(steps):
            x += x_increment
            y += y_increment
            rx = round(x)
            ry = round(y)
            self.grid[ry][rx] = 1

    def printGrid(self):
        for r in range(len(self.grid)):
            for c in range(len(self.grid[r])):
                if self.grid[r][c]: print("x", end="")
                else: print(" ", end="")
            print()
    
    def _generateExteriorChainCode(self, x=0, y=0):
        self.exterior_cc = []
        x1, y1 = x, y
        while not self.grid[y1][x1]:
            x1 += 1
            if x1 == self.grid_w:
                x1 = 0
                y1 += 1
                if y1 == self.grid_h:
                    return
        self.exterior_origin = (x1, y1)
        for c in range(8):
            v = CC_TO_VECTOR[c]
            x2 = x1 + v[0]
            y2 = y1 + v[1]
            if 0 <= x2 < self.grid_w and 0 <= y2 < self.grid_h:
                if self.grid[y2][x2]:
                    self.exterior_cc.append(c)
                    x1 = x2
                    y1 = y2
                    last_c = c
                    break
        while (x1, y1) != self.exterior_origin:
            last_c = (last_c + 5) % 8
            for i in range(7):
                c = (last_c + i) % 8
                v = CC_TO_VECTOR[c]
                x2 = x1 + v[0]
                y2 = y1 + v[1]
                if 0 <= x2 < self.grid_w and 0 <= y2 < self.grid_h:
                    if self.grid[y2][x2]:
                        self.exterior_cc.append(c)
                        x1 = x2
                        y1 = y2
                        last_c = c
                        break

    def getExteriorPoints(self):
        self._generateExteriorChainCode()
        x1, y1 = self.exterior_origin
        x1 += self.grid_shift[0]
        y1 += self.grid_shift[1]
        points = [(x1,y1)]
        polygon_pts = [(x1,y1)]
        for i in range(len(self.exterior_cc)-1):
            c1 = self.exterior_cc[i]
            v1 = CC_TO_VECTOR[c1]
            x1 += v1[0]
            y1 += v1[1]
            polygon_pts.append((x1,y1))
            c2 = self.exterior_cc[i+1]
            v2 = CC_TO_VECTOR[c2]
            x2 = x1 + v2[0]
            y2 = y1 + v2[1]
            if polygonArea(polygon_pts + [(x2, y2)]) > 8: # check area of polygon two points ahead
                pt1 = polygon_pts[-2]
                pt2 = polygon_pts[-1]
                points.append(pt1)
                polygon_pts = [pt1, pt2]
        return points
    
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
    
    def getMergedPoints(self):
        grid_copy = self.grid.copy()
        grid_contains_contours = True
        merged_contours = []
        num_exteriors = 0
        while grid_contains_contours:
            self._generateExteriorChainCode()
            if not self.exterior_cc:
                grid_contains_contours = False
            else:
                num_exteriors += 1
                x1, y1 = self.exterior_origin
                self._deleteContour(x1, y1)
                x1 += self.grid_shift[0]
                y1 += self.grid_shift[1]
                points = [(x1,y1)]
                polygon_pts = [(x1,y1)]
                for i in range(len(self.exterior_cc)-1):
                    c1 = self.exterior_cc[i]
                    v1 = CC_TO_VECTOR[c1]
                    x1 += v1[0]
                    y1 += v1[1]
                    polygon_pts.append((x1,y1))
                    c2 = self.exterior_cc[i+1]
                    v2 = CC_TO_VECTOR[c2]
                    x2 = x1 + v2[0]
                    y2 = y1 + v2[1]
                    if polygonArea(polygon_pts + [(x2, y2)]) > 8: # check area of polygon two points ahead
                        pt1 = polygon_pts[-2]
                        pt2 = polygon_pts[-1]
                        points.append(pt1)
                        polygon_pts = [pt1, pt2]
                merged_contours.append(points)
        self.grid = grid_copy
        if num_exteriors == len(self.contours):
            return None
        else:
            return merged_contours

# shoelace formula (source: https://algorithmtutor.com/Computational-Geometry/Area-of-a-polygon-given-a-set-of-points/)
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
