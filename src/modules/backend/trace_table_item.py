from PySide6.QtGui import QTransform

from modules.calc.quantification import area, lineDistance

from modules.pyrecon.trace import Trace

class TraceTableItem():

    def __init__(self, trace : Trace, t : list):
        """Create an object table item.
        
            Params:
                name (str): the name of the trace
        """
        self.trace = trace
        self.name = trace.name
        self.closed = trace.closed
        self.tags = trace.tags
        tform = QTransform(t[0], t[3], t[1], t[4], t[2], t[5])
        tformed_points = [tform.map(*p) for p in trace.points]
        self.length = lineDistance(tformed_points, closed=trace.closed)
        if not self.closed:
            self.area = 0
        else:
            self.area = area(tformed_points)
        self.radius = trace.getRadius(t)
    
    def isTrace(self, trace : Trace):
        """Compares the traces (must be the SAME OBJECT in python)."""
        return trace == self.trace
    
    def getTags(self):
        return self.tags

    def getLength(self):
        return self.length
    
    def getArea(self):
        return self.area
    
    def getRadius(self):
        return self.radius