class Trace():

    def __init__(self, name, color, closed=True, exported=False):
        self.name = name
        self.color = color
        self.closed = closed
        self.points = []
        self.hidden = False

        # for translation between Reconstruct and pyReconstruct
        self.exported = exported
    
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
    
    def setExported(self, exported):
        self.exported = exported

    def getDict(self):
        return self.__dict__
    
    def fromDict(d):
        """Create a Contour object from a dictionary"""
        new_trace = Trace(d["name"], d["color"], d["closed"], d["exported"])
        new_trace.points = d["points"]
        new_trace.setHidden(d["hidden"])
        return new_trace