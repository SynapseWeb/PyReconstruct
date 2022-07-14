# 2022-07-07 for Julian
# Note that function centroid makes use of function area
import math

def area(pts : list) -> float:
    """Find the area of a closed contour.
    
        Params:
            pts (list): list of points describing a closed contour
        Returns:
            (float) the area of the closed contour
    """
    if pts[0] != pts[-1]:
        pts = pts + pts[:1]
    x = [ c[0] for c in pts ]
    y = [ c[1] for c in pts ]
    s = 0
    for i in range(len(pts) - 1):
        s += x[i]*y[i+1] - x[i+1]*y[i]
    return abs(s/2)

def centroid(pts : list) -> tuple:
    """Find the location of centroid.
    
        Params:
            pts (list): points describing a contour
        Returns:
            (tuple) coordinate pair of the centroid
    """
    if pts[0] != pts[-1]:
        pts = pts + pts[:1]
    x = [ c[0] for c in pts ]
    y = [ c[1] for c in pts ]
    sx = sy = 0
    a = area(pts)
    for i in range(len(pts) - 1):
        sx += (x[i] + x[i+1])*(x[i]*y[i+1] - x[i+1]*y[i])
        sy += (y[i] + y[i+1])*(x[i]*y[i+1] - x[i+1]*y[i])
    return (round(sx/(6*a), 5), round(sy/(6*a), 5))

def distance(x1 : float, y1 : float, x2 : float, y2 : float) -> float:
    """Calculate Euclidean distance between two points in 2D space.
    
        Params:
            x1 (float): x-value of first point
            y1 (float): y-value of first point
            x2 (float): x-value of second point
            y2 (float): y-value of second point
        Returns:
            (float) the distance between the two points
    """
    dist = ((x1-x2)**2 + (y1-y2)**2) ** 0.5
    return dist

def lineDistance(pts : list, closed=True) -> float:
    """Calculate distance along multi-vertex line.

        Params:
            pts (list): a list describing a contour
            closed (bool): whether or not the contour is closed
        Return:
            (float) the length of the contour
    """
    # x and y represent a list of x- and y-coordinates.
    x = [ c[0] for c in pts ]
    y = [ c[1] for c in pts ]
    dist = 0.0
    n = len(x) - 1
    for i in range(n):
        point_dist = distance(x[i], y[i], x[i+1], y[i+1])
        dist += point_dist
    if closed:  # if closed make one more calculation
        point_dist = distance(x[-1], y[-1], x[0], y[0])
        dist += point_dist
    return round(dist, 7)

def sigfigRound(n : float, sf : int) -> float:
    """Round a float to a specified number of significant figures.
    
        Params:
            n (float): the number to be rounded
            sf (int): the number of significant figures to keep
        Returns:
            (float) the rounded number
    """
    if n == 0:
        return 0
    greatest_place = math.floor(math.log(abs(n))/math.log(10))
    return round(n, sf - (greatest_place+1))
