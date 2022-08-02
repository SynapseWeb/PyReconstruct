import numpy as np

from quantification import area

CC_TO_VECTOR = ((1,0), (1,1), (0,1), (-1,1), (-1,0), (-1,-1), (0,-1), (1,-1))  

class ZarrGrid():

    def __init__(self, grid : np.ndarray):
        """Create a grid object.
        
            Params:
                grid (ndarray): boolean grid of a neuroglancer object"""
        self.grid = grid
        self.grid_h, self.grid_w = self.grid.shape

    
    def printGrid(self):
        """Print the grid to the console.
        
        Mostly for debugging purposes.
        """
        for r in range(len(self.grid)):
            for c in range(len(self.grid[r])):
                if self.grid[r, c]: print("X", end="")
                else: print(" ", end="")
            print()
    
    def _deleteContour(self, x : int, y : int):
        """Delete the object on the grid at a given point.
        
            Params:
                x (int): x-value of point on contour
                y (int) y-value of point on contour
        """
        stack = [(x,y)] # use a stack instead of recursion
        while stack:
            x1, y1 = stack.pop()
            if self.grid[y1, x1]:
                self.grid[y1, x1] = False
                for i in range(8):
                    v = CC_TO_VECTOR[i]
                    x2 = x1 + v[0]
                    y2 = y1 + v[1]
                    if 0 <= x2 < self.grid_w and 0 <= y2 < self.grid_h:
                        stack.append((x2,y2))
    
    def generateExterior(self, x=0, y=0, delete=False) -> list:
        """Get the exterior contour of an object on the grid.
        
            Params:
                x (int): x-value of point on object
                y (int): y-value of point on object
                delete (bool): whether or not to delete the contour when finished
            Returns:
                (list) the exterior contour of the object
        """
        # search the grid until an object is found
        x1, y1 = x, y
        while not self.grid[y1, x1]:
            x1 += 1
            if x1 == self.grid_w:
                x1 = 0
                y1 += 1
                if y1 == self.grid_h:
                    return
        last_c = 0
        exterior_origin = (x1, y1)  # save object location
        exterior = [exterior_origin]
        last_c = (last_c + 4) % 8  # invert the last chain code direction
        for i in range(1, 8):
            c = (last_c + i) % 8  # search for the next point starting from the outside
            v = CC_TO_VECTOR[c]
            x2 = x1 + v[0]
            y2 = y1 + v[1]
            if 0 <= x2 < self.grid_w and 0 <= y2 < self.grid_h:
                if self.grid[y2, x2]:
                    exterior.append((x2, y2))
                    x1 = x2
                    y1 = y2
                    last_c = c
                    break
        # begin traveling around the object
        while (x1, y1) != exterior_origin:
            last_c = (last_c + 4) % 8  # invert the last chain code direction
            for i in range(1, 8):
                c = (last_c + i) % 8  # search for the next point starting from the outside
                v = CC_TO_VECTOR[c]
                x2 = x1 + v[0]
                y2 = y1 + v[1]
                if 0 <= x2 < self.grid_w and 0 <= y2 < self.grid_h:
                    if self.grid[y2, x2]:
                        exterior.append((x2, y2))
                        x1 = x2
                        y1 = y2
                        last_c = c
                        break
        # delete the contour if requested
        if delete:
            self._deleteContour(*exterior_origin)
        return exterior
    
    def getAllContours(self) -> list:
        """Get all the exterior contours for objects on the grid.
        
            Returns:
                (list): list of all contours"""
        grid_copy = self.grid.copy() # copy the grid
        all_contours = []
        exterior = self.generateExterior(0, 0, delete=True)
        while exterior is not None: # exterior will be None when none are left
            all_contours.append(exterior)
            exterior = self.generateExterior(*exterior[0], delete=True)
        self.grid = grid_copy # restore the original grid
        return all_contours


def reducePoints(points : list) -> list:
    """Remove points the do not contribute further information to a contour.
    
        Params:
            points (list): list of points describing contour
        Returns:
            (list) reduced points
    """
    reduced_points = [points[0]]
    start_i = 0
    end_i = 2
    while end_i < len(points) - 1:
        a = area(points[start_i : end_i+1])
        if a > 1:
            reduced_points.append(points[end_i-1])
            start_i = end_i - 1
            end_i = start_i + 2
        else:
            end_i += 1
    return reduced_points

from PIL import Image
im = Image.open("test.bmp").convert("L")
p = np.array(im)
grid = p.astype(bool)
zgrid = ZarrGrid(grid)
contours = zgrid.getAllContours()

outlines = np.zeros(grid.shape, bool)
for contour in contours:
    for point in contour:
        outlines[point[1], point[0]] = True
outlines_im = Image.fromarray(outlines)
outlines_im.save("outlines.bmp")

reduced = np.zeros(grid.shape, bool)
for contour in contours:
    red = reducePoints(contour)
    for point in red:
        reduced[point[1], point[0]] = True
reduced_im = Image.fromarray(reduced)
reduced_im.save("reduced.bmp")



