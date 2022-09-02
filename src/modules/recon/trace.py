class Trace():

    def __init__(self, name : str, color : tuple, closed=True, mode=11):
        """Create a Trace object.
        
            Params:
                name (str): the name of the trace
                color (tuple): the color of the trace: (R, G, B) 0-255
                closed (bool): whether or not the trace is closed
                mode (int): the display mode of the trace (XML use)
        """
        self.name = name
        self.color = color
        self.closed = closed
        self.points = []
        self.hidden = False  # default to False
        self.mode = mode  # not used in this program, but stored for XML file purposes
    
    def add(self, point : tuple):
        """Add a point to the trace.
        
            Params:
                point (tuple): a coordinate pair"""
        self.points.append(point)
    
    def isSameTrace(self, other) -> bool:
        """Check if traces have the same name, color, and points.
        
            Params:
                other (Trace): the trace to compare
            Returns:
                (bool) whether or not the traces are the same
        """
        if self.name != other.name:
            return False
        if self.color != other.color:
            return False
        if self.points != other.points:
            return False
        return True
    
    def setHidden(self, hidden=True):
        """Set whether the trace is hidden.
        
            Params:
                hidden (bool): whether the trace is hidden
        """
        self.hidden = hidden

    def getDict(self) -> dict:
        """Return the trace data as a dictionary.
        
            Returns:
                (dict) Dictionary containing the trace data
        """
        return self.__dict__
    
    # STATIC METHOD
    def fromDict(d):
        """Create a Contour object from a dictionary.
        
            Params:
                d (dict): the dictionary contour data
            Returns:
                (Trace) a Trace object constructed from the dictionary data
        """
        new_trace = Trace(d["name"], d["color"], d["closed"], d["mode"])
        new_trace.points = d["points"]
        new_trace.setHidden(d["hidden"])
        return new_trace
    
    def getBounds(self, tform=None) -> tuple:
        """Get the most extreme coordinates for the trace.
        
            Params:
                tform (QTransform): optional parameter to find extremeties of transformed trace
            Returns:
                (float) min x value
                (float) min y value
                (float) max x value
                (float) max y value
        """
        if tform is None:
            x = [p[0] for p in self.points]
            y = [p[1] for p in self.points]
        else:
            tform_points = [tform.map(*p) for p in self.points]
            x = [p[0] for p in tform_points]
            y = [p[1] for p in tform_points]
        return min(x), min(y), max(x), max(y)