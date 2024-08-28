"""Calculate Feret diameters.

Sourced from:
http://code.activestate.com/recipes/117225-convex-hull-and-diameter-of-2d-point-sets/

"""

from math import sqrt


def orientation(p,q,r):
    """Return positive if p-q-r are clockwise, neg if ccw, zero if colinear."""
    
    return (q[1]-p[1])*(r[0]-p[0]) - (q[0]-p[0])*(r[1]-p[1])


def hulls(Points):
    """Graham scan to find upper and lower convex hulls of a set of 2d points."""
    U = []
    L = []
    
    Points.sort()
    
    for p in Points:
        
        while len(U) > 1 and orientation(U[-2],U[-1],p) <= 0: U.pop()
        while len(L) > 1 and orientation(L[-2],L[-1],p) >= 0: L.pop()
        U.append(p)
        L.append(p)
        
    return U, L


def rotatingCalipers(Points):
    """Given a list of 2d points, finds all ways of sandwiching the points
between two parallel lines that touch one point each, and yields the sequence
of pairs of points touched by each pair of lines."""
    U, L = hulls(Points)
    
    i = 0
    j = len(L) - 1
    
    while i < len(U) - 1 or j > 0:
        
        yield U[i],L[j]
        
        # if all the way through one side of hull, advance the other side
        if i == len(U) - 1:

            j -= 1
        
        elif j == 0:

            i += 1
        
        # still points left on both lists, compare slopes of next hull edges
        # being careful to avoid divide-by-zero in slope calculation
        elif (U[i+1][1]-U[i][1])*(L[j][0]-L[j-1][0]) > \
                (L[j][1]-L[j-1][1])*(U[i+1][0]-U[i][0]):

            i += 1
            
        else: j -= 1


def feret(Points):
    """Given a list of 2d points, returns the minimum and maximum feret diameters."""
    sq_dist_pairs = [((p[0]-q[0])**2 + (p[1]-q[1])**2, (p,q)) for p, q in rotatingCalipers(Points)]
    min_feret_sq, _ = min(sq_dist_pairs)
    max_feret_sq, _ = max(sq_dist_pairs)
    return sqrt(min_feret_sq), sqrt(max_feret_sq)
