class Trace():

    def __init__(self, name, color, closed=True):
        self.name = name
        self.color = color
        self.closed = closed
        self.points = []
        self.hidden = False
    
    def add(self, point):
        """Add a point to the trace"""
        self.points.append(point)
    
    def isSameTrace(self, other):
        if self.name != other.name:
            return False
        if self.color != other.color:
            return False
        if self.points != other.points:
            return False
        return True
    
    def setHidden(self, hidden=True):
        self.hidden = hidden

    def getDict(self):
        return self.__dict__
    
    def fromDict(d):
        """Create a Contour object from a dictionary"""
        new_trace = Trace(d["name"], d["color"], d["closed"])
        new_trace.points = d["points"]
        new_trace.setHidden(d["hidden"])
        return new_trace
    
    def getBounds(self, tform=None):
        if tform is None:
            x = [p[0] for p in self.points]
            y = [p[1] for p in self.points]
        else:
            tform_points = [tform.map(*p) for p in self.points]
            x = [p[0] for p in tform_points]
            y = [p[1] for p in tform_points]
        return min(x), min(y), max(x), max(y)