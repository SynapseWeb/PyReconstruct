"""Math formulae."""


import math
import cv2
import numpy as np
from typing import List

from scipy.interpolate import interp1d


def area(pts : list) -> float:
    """Find the area of a closed contour.
    
        Params:
            pts (list): list of points describing a closed contour
        Returns:
            (float) the area of the closed contour
    """
    if len(pts) <= 2:
        return 0
    
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
    a = area(pts)
    # if area is greater than 0
    if abs(a) > 1e-6:
        if pts[0] != pts[-1]:
            pts = pts + pts[:1]
        if not ccwpoly(pts):
            pts = pts[::-1]
        x = [ c[0] for c in pts ]
        y = [ c[1] for c in pts ]
        sx = sy = 0
        for i in range(len(pts) - 1):
            sx += (x[i] + x[i+1])*(x[i]*y[i+1] - x[i+1]*y[i])
            sy += (y[i] + y[i+1])*(x[i]*y[i+1] - x[i+1]*y[i])
        return (round(sx/(6*a), 6), round(sy/(6*a), 6))
    # if area is 0: return average of points
    else:
        x_avg = sum([p[0] for p in pts])/len(pts)
        y_avg = sum([p[1] for p in pts])/len(pts)
        return round(x_avg, 6), round(y_avg, 6)


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


def euclidean_distance(p1: tuple, p2: tuple):
    """Calculate Euclidean distance between two points."""

    return np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)


def distance3D(x1 : float, y1 : float, z1 : float, x2 : float, y2 : float, z2 : float) -> float:
    """Calculate Euclidean distance between two points in 3D space.
    
        Params:
            x1 (float): x-value of first point
            y1 (float): y-value of first point
            z1 (float): z-value of fist point
            x2 (float): x-value of second point
            y2 (float): y-value of second point
            z2 (float): z-value of second point
        Returns:
            (float) the distance between the two points
    """
    dist = ((x1-x2)**2 + (y1-y2)**2 + (z2-z1)**2) ** 0.5
    return dist


def lineDistance(pts : list, closed=True) -> float:
    """Calculate distance along multi-vertex line.

        Params:
            pts (list): a list describing a contour
            closed (bool): whether or not the contour is closed
        Return:
            (float) the length of the contour
    """
    if len(pts) <= 1:
        return 0
    
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


def getDistanceFromTrace(x : float, y: float, trace : list, factor=1.0, absolute=True):
    """Find the distance a point is from a given trace (uses opencv).
    
        Params:
            x (float): the x-coord of the point
            y (float): the y-coord of the point
            trace (list): the trace to check against the point
        Returns:
            (float) the distance of the point from the trace
    """
    pp_test = cv2.pointPolygonTest((np.array(trace) * factor).astype(int), (x * factor, y * factor), measureDist=True)
    return abs(pp_test / factor) if absolute else pp_test / factor


def pointInPoly(x : float, y: float, trace : list) -> bool:
    """Find if a point is in a given trace (uses opencv).
    
        Params:
            x (float): the x-coord of the point
            y (float): the y-coord of the point
            trace (list): the trace to check against the point
        Returns:
            (bool): whether or not the point is in the trace
    """
    pp_test = cv2.pointPolygonTest(np.array(trace).astype(int), (x, y), measureDist=False)
    return pp_test >= 0


def ccwpoly(pts):
    s = 0
    for i in range(len(pts)):
        x1, y1 = pts[i-1]
        x2, y2 = pts[i]
        s += (x2 - x1) * (y2 + y1)
    return s < 0


# source: https://stackoverflow.com/questions/3838329/how-can-i-check-if-two-segments-intersect
def ccw(A,B,C):
    return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])


def linesIntersect(A, B, C, D):
    """Return true if line segments AB and CD intersect."""
    return ccw(A,C,D) != ccw(B,C,D) and ccw(A,B,C) != ccw(A,B,D)


def lineIntersectsContour(x1, y1, x2, y2, contour, closed=True):
    p1 = (x1, y1)
    p2 = (x2, y2)
    if closed:
        start = 0
    else:
        start = 1
    for i in range(start, len(contour)):
        p3 = contour[i-1]
        p4 = contour[i]
        if linesIntersect(p1, p2, p3, p4):
            return True
    return False


def colorize(n):
    cn = (n % 156) ** 3
    c = [0, 0, 0]
    for i in range(3):
        c[i] = cn % 156 + 100
        cn //= 156
    return c


def ellipseFromPair(x1, y1, x2, y2, number=100):
    """Create an ellipse from two points in space."""
    center = (
        (x1 + x2) / 2,
        (y1 + y2) / 2
    )
    a = abs(x1 - center[0])
    b = abs(y1 - center[1])

    ellipse = []
    for i in range(number):
        ellipse.append((
            round(center[0] + a * math.cos((i / number) * 2 * math.pi)),
            round(center[1] + b * math.sin((i / number) * 2 * math.pi))
        ))
    
    return ellipse


def get_window_points(points, idx, max_size, edge_mode):
    """Get points for window centered at idx with given maximum size.
    
    Params:
        points (list): list of [x, y, snum] points
        idx (int): center index for the window
        max_size (int): maximum window size
        edge_mode (str): how to handle edges - "padded", "shrinking", or "circular"
        
    Returns:
        tuple: (window_x, window_y) lists of x and y coordinates
    """
    if edge_mode == "shrinking":
        
        ## Calculate growing window size from ends
        dist_from_start = idx
        dist_from_end = len(points) - 1 - idx
        dist_from_edge = min(dist_from_start, dist_from_end)

        ## Window size grows from 1 at edges to max_size in middle
        current_size = min(1 + 2 * dist_from_edge, max_size)
        half = current_size // 2
        start_idx = idx - half
        end_idx = idx + half + 1

        return (
            [p[0] for p in points[start_idx:end_idx]], 
            [p[1] for p in points[start_idx:end_idx]]
        )
        
    else:
        
        half = max_size // 2
        window_x = []
        window_y = []
        
        for i in range(-half, half + 1):
            
            if edge_mode == "circular":
                point_idx = (idx + i) % len(points)
                
            else:  # padded
                point_idx = max(0, min(idx + i, len(points) - 1))
            
            window_x.append(points[point_idx][0])
            window_y.append(points[point_idx][1])
            
        return window_x, window_y


def rolling_average(points, window=10, edge_mode="padded"):
    """Smooth z-trace with configurable edge handling.
    
    Params:
        series (Series): the series object (contains transform data)
        smooth (int): the smoothing factor
        edge_mode (str): how to handle edges - "padded", "shrinking", or "circular"
    """
    if edge_mode not in ["padded", "shrinking", "circular"]:
        raise ValueError("edge_mode must be 'padded', 'shrinking', or 'circular'")

    new_points = [None] * len(points)

    # Process each point
    for i in range(len(points)):
        
        ## Get window points
        window_x, window_y = get_window_points(points, i, window, edge_mode)
        
        ## Calculate moving average
        window_size = len(window_x)  # window len variable depending on edge mode
        xMA = sum(window_x) / window_size
        yMA = sum(window_y) / window_size
        
        ## Update point with smoothed values
        new_points[i] = (
            round(xMA, 4),
            round(yMA, 4)
        )

    return new_points


def interpolate_points(points: List[tuple], spacing=0.01):
    """Interpolate points around a path."""

    x, y = zip(*points)

    ## Calculate cumulative arc lengths (distances between consecutive points)
    distances = [0]
    
    for i in range(1, len(points)):
        
        distances.append(
            distances[-1] + euclidean_distance(points[i-1], points[i])
        )

    ## Total path length
    total_length = distances[-1]

    ## Interpolate curve using parametric functions
    interp_x = interp1d(distances, x)
    interp_y = interp1d(distances, y)

    # Generate new distances at equal intervals
    num_new_points = int(total_length / spacing)
    new_distances = np.linspace(0, total_length, num_new_points)

    # Interpolate new points at these distances
    x_new = [round(elem, 5) for elem in interp_x(new_distances)]
    y_new = [round(elem, 5) for elem in interp_y(new_distances)]

    return list(
        zip(x_new, y_new)
    )
