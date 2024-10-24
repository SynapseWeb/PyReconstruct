"""Math formulae."""


import math
import cv2
import numpy as np
from typing import List

from scipy.interpolate import CubicSpline


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


def pad_circular_points(points, padding):
    """Add padding to a circular path."""

    if padding == 0:

        return points

    indices = np.arange(len(points))
    
    padded_indices = np.concatenate([
        indices[-padding:],
        indices,
        indices[:padding]
    ], axis=0)

    return [points[i] for i in list(padded_indices)]


def pad_open_points(points, padding):
    """Add padding to an open path by extending endpoints."""

    if padding == 0:

        return points

    x_vals, y_vals = map(list, zip(*points))

    x_vals = [x_vals[0]] * padding + x_vals + [x_vals[-1]] * padding
    y_vals = [y_vals[0]] * padding + y_vals + [y_vals[-1]] * padding

    return list(
        zip(x_vals, y_vals)
    )


def rolling_average(points, window, circular=True, as_int=False):
    """Calculate rolling average of a path."""

    if window %2 == 0:
        raise ValueError("Window size must be odd to avoid asymmetric smoothing")

    n_points = len(points)    
    half_window = window // 2
    smooth = [0] * n_points  # empty

    if circular:  # closed traces

        points = pad_circular_points(points, half_window)

    else:

        points = pad_open_points(points, half_window)

    points = np.asarray(points)
            
    for i in range(half_window, n_points + half_window):

        start = i - half_window
        end = i + half_window + 1

        mean = np.mean(
            points[start:end],
            axis=0
        )

        smooth[start] = (
            round(mean[0], 5),
            round(mean[1], 5)
        )
                
    if as_int:

        return [(int(elem[0]), int(elem[1])) for elem in smooth]

    return smooth


def interpolate_points(points: List[tuple], spacing=0.01):
    """Interpolate points around a path."""

    ## Determine if path open or closed
    if points[0] != points[-1]:  # open path
        bound_cond = "not-a-knot"
    else:  # closed pathp
        bound_cond = "periodic"

    x, y = zip(*points)

    ## Calculate cumulative arc lengths (distances between consecutive points)
    distances = [0]
    
    for i in range(1, len(points)):
        
        distances.append(distances[-1] + euclidean_distance(points[i-1], points[i]))

    ## Total path length
    total_length = distances[-1]

    ## Create cubic splines for x and y based on distances
    cs_x = CubicSpline(distances, x, bc_type=bound_cond)
    cs_y = CubicSpline(distances, y, bc_type=bound_cond)

    # Generate new distances at equal intervals
    num_new_points = int(total_length / spacing)
    new_distances = np.linspace(0, total_length, num_new_points)

    # Interpolate new points at these distances
    x_new = [round(elem, 5) for elem in cs_x(new_distances)]
    y_new = [round(elem, 5) for elem in cs_y(new_distances)]

    return list(
        zip(x_new, y_new)
    )
