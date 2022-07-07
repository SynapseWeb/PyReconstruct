# 2022-07-07 for Julian
# Note that function centroid makes use of function area

def area(pts):
    """Area of cross-section."""
    if pts[0] != pts[-1]:
        pts = pts + pts[:1]
    x = [ c[0] for c in pts ]
    y = [ c[1] for c in pts ]
    s = 0
    for i in range(len(pts) - 1):
        s += x[i]*y[i+1] - x[i+1]*y[i]
    return s/2

def centroid(pts):
    """Location of centroid."""
    if pts[0] != pts[-1]:
        pts = pts + pts[:1]
    x = [ c[0] for c in pts ]
    y = [ c[1] for c in pts ]
    sx = sy = 0
    a = area(pts)
    for i in range(len(pts) - 1):
        sx += (x[i] + x[i+1])*(x[i]*y[i+1] - x[i+1]*y[i])
        sy += (y[i] + y[i+1])*(x[i]*y[i+1] - x[i+1]*y[i])
    return [round(sx/(6*a), 5), round(sy/(6*a), 5)]

def calcDistance(x1, y1, x2, y2):
    """Calculate Euclidean distance between two points in 2D space."""
    dist = np.sqrt((x1-x2)**2 + (y1-y2)**2)
    return dist

def calcLineDistance(x, y, closed = "true"):
    """Calculate distance along multi-vertex line.

    x and y represent a list of x- and y-coordinates.
    """
    dist = 0.0
    n = len(x) - 1
    for i in range(n):
        point_dist = calcDistance(x[i], y[i], x[i+1], y[i+1])
        dist += point_dist
    if closed == "true":  # if closed make one more calculation
        point_dist = calcDistance(x[-1], y[-1], x[0], y[0])
        dist += point_dist
    return round(dist, 7)
