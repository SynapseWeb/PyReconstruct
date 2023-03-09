# 2022-07-07 for Julian
# Note that function centroid makes use of function area
import math
import cv2
import numpy as np
from itertools import combinations
from modules.pyrecon.transform import Transform

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

def distance3D(x1 : float, y1 : float, z1 : float, x2 : float, y2 : float, z2 : float) -> float:
    """Calculate Euclidean distance between two points in 2D space.
    
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

# source: https://stackoverflow.com/questions/3838329/how-can-i-check-if-two-segments-intersect
def ccw(A,B,C):
    return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])

# Return true if line segments AB and CD intersect
def linesIntersect(A,B,C,D):
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

def estimateLinearTform(pts1, pts2):
    """Estimate the transform that converts pts1 to pts2."""
    combs = tuple(combinations(range(len(pts1)), 3))
    sum_mat = np.zeros((2, 3), dtype=np.float32)
    for c in combs:
        trip1 = [pts1[i] for i in c]
        trip2 = [pts2[i] for i in c]
        mat = cv2.getAffineTransform(
            np.array(trip1, dtype=np.float32),
            np.array(trip2, dtype=np.float32)
        )
        sum_mat += mat
    avg_mat = sum_mat / len(combs)
    tform = Transform(avg_mat.reshape(1,6).tolist()[0])

    return tform

# def estimateLinearTform(pts1, pts2):
#     """Estimate the transform that converts pts1 to pts2."""
#     combs = tuple(combinations(range(len(pts1)), 3))
#     estimated_tform = None
#     estimated_error = 0
#     for c in combs:
#         trip1 = [pts1[i] for i in c]
#         trip2 = [pts2[i] for i in c]
#         mat = cv2.getAffineTransform(
#             np.array(trip1, dtype=np.float32),
#             np.array(trip2, dtype=np.float32)
#         )
#         tform = Transform(mat.reshape(1,6).tolist()[0])
#         predicted_trip2 = tform.map(trip1)
#         error = sum([distance(*trip2[i], *predicted_trip2[i]) for i in range(3)])
#         if estimated_tform is None or error < estimated_error:
#             estimated_tform = tform
#             estimated_error = error

#     return estimated_tform