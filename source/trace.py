class Trace():

    def __init__(self, name, color, closed=True):
        self.name = name
        self.color = color
        self.closed = closed
        self.points = []
    
    def add(self, point):
        """Add a point to the trace"""
        self.points.append(point)
    
    def getDict(self):
        return self.__dict__
    
    def fromDict(d):
        """Create a Contour object from a dictionary"""
        new_trace = Trace(d["name"], d["color"], d["closed"])
        new_trace.points = d["points"]
        return new_trace