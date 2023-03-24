from modules.calc import area, lineDistance
from .trace import Trace
from .transform import Transform

class TraceTableItem():

    def __init__(self, trace : Trace, tform : Transform, index : int):
        """Create a trace table item.
        
            Params:
                trace (Trace): the trace object for the trace
                t (list): the list as a transform
                index (int): the index of the trace in the contour
        """
        self.trace = trace
        self.name = trace.name
        self.index = index
        self.closed = trace.closed
        self.tags = trace.tags
        tformed_points = tform.map(trace.points)
        self.length = lineDistance(tformed_points, closed=trace.closed)
        if not self.closed:
            self.area = 0
        else:
            self.area = area(tformed_points)
        self.radius = trace.getRadius(tform)
    
    def isTrace(self, trace : Trace):
        """Compares the traces (must be the SAME PYTHON OBJECT)."""
        return trace == self.trace
    
    def getTags(self):
        return self.tags

    def getLength(self):
        return self.length
    
    def getArea(self):
        return self.area
    
    def getRadius(self):
        return self.radius