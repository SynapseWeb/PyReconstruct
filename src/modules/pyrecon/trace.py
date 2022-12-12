from modules.backend.grid import reducePoints

from modules.pyrecon.transform import Transform
from modules.pyrecon.trace_log import TraceLog

from modules.legacy_recon.classes.contour import Contour as XMLContour
from modules.legacy_recon.classes.transform import Transform as XMLTransform

from modules.calc.quantification import centroid, distance

class Trace():

    def __init__(self, name : str, color : tuple, closed=True):
        """Create a Trace object.
        
            Params:
                name (str): the name of the trace
                color (tuple): the color of the trace: (R, G, B) 0-255
                closed (bool): whether or not the trace is closed
        """
        self.name = name
        self.color = color
        self.closed = closed
        self.negative = False
        self.points = []
        self.hidden = False  # default to False
        self.tags = set()
        self.history = []

        # extra hidden attributes for XML support
        self.mode = 11
    
    def copy(self):
        """Create a copy of the trace object.
        
            Returns:
                (Trace): a copy of the object
        """
        copy_trace = Trace("", [0,0,0])
        copy_trace.__dict__ = self.__dict__.copy()
        copy_trace.points = self.points.copy()
        copy_trace.tags = self.tags.copy()
        copy_trace.history = [l.copy() for l in self.history]
        return copy_trace
    
    def add(self, point : tuple):
        """Add a point to the trace.
        
            Params:
                point (tuple): a coordinate pair
        """
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
    
    def addTag(self, tag : str):
        """Set the tag for the trace:
            
            Params:
                tag (str): the tag for the trace
        """
        self.tags.append(tag)

    def getDict(self, include_name=True) -> dict:
        """Return the trace data as a dictionary.
        
            Params:
                include_name (bool): True if name should be included in dict
            Returns:
                (dict) dictionary containing the trace data
        """
        d = {}
        if include_name:
            d["name"] = self.name
        d["color"] = self.color
        d["closed"] = self.closed
        d["negative"] = self.negative
        d["x"], d["y"] = [], []
        for p in self.points:
            d["x"].append(round(p[0], 7))
            d["y"].append(round(p[1], 7))
        d["hidden"] = self.hidden
        d["mode"] = self.mode
        d["tags"] = list(self.tags)
        d["history"] = [list(l) for l in self.history]
        return d
    
    def getXMLObj(self, xml_image_tform : XMLTransform = None) -> XMLContour:
        """Returns the trace data as an XML object.
            Params:
                xml_image_tform (XMLTransform): the xml image transform object
            Returns:
                (XMLContour) the trace as an xml contour object
        """
        border_color = list(self.color)
        for i in range(len(border_color)):
            border_color[i] /= 255
        xml_contour = XMLContour(
            name = self.name,
            comment = "",
            hidden = self.hidden,
            closed = self.closed,
            simplified = False,
            mode = self.mode,
            border = border_color,
            fill = border_color,
            points = self.points,
            transform = xml_image_tform
        )
        return xml_contour
    
    # STATIC METHOD
    def fromDict(d, name : str = None):
        """Create a trace object from a dictionary.
        
            Params:
                d (dict): the dictionary contour data
                name (str): the name of the trace
            Returns:
                (Trace) a Trace object constructed from the dictionary data
        """
        if not name:
            name = d["name"]
        new_trace = Trace(name, d["color"], d["closed"])
        new_trace.negative = d["negative"]
        new_trace.points = list(zip(d["x"], d["y"]))
        new_trace.hidden = d["hidden"]
        new_trace.mode = d["mode"]
        new_trace.tags = set(d["tags"])
        new_trace.history = [TraceLog(l) for l in d["history"]]
        return new_trace
    
    # STATIC METHOD
    def dictFromXMLObj(xml_trace : XMLContour, tform : Transform = None, section_mag=None, palette=False):
        """Create a trace from an xml contour object.
        
            Params:
                xml_trace (XMLContour): the xml contour object
                xml_image_tform (XMLTransform): the xml image transform object
            Returns:
                (Trace) the trace object
        """
        # get basic attributes
        name = xml_trace.name
        color = list(xml_trace.border)
        for i in range(len(color)):
            color[i] = int(color[i] * 255)
        closed = xml_trace.closed
        points = xml_trace.points.copy()
        new_trace = Trace(name, color, closed)

        # get the transform
        if xml_trace.transform is not None:
            points = xml_trace.transform.transformPoints(xml_trace.points)
        if tform is not None:
            points = tform.map(points, inverted=True)
        
        # get the points
        if section_mag:
            new_trace.points = reducePoints(
                points,
                closed=new_trace.closed,
                mag=2/section_mag
            )
        else:
            new_trace.points = points
        new_trace.mode = xml_trace.mode

        if not palette:
            new_trace.addLog("Imported")
        
        return new_trace.getDict()

    def getBounds(self, tform : Transform = None) -> tuple:
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
            tform_points = tform.map(self.points)
            x = [p[0] for p in tform_points]
            y = [p[1] for p in tform_points]
        
        return min(x), min(y), max(x), max(y)
    
    def getRadius(self, tform : Transform = None):
        """Get the distance from the centroid of the trace to its farthest point.
        
            Params:
                tform (Transform): the transform to apply to the points
        """
        points = self.points.copy()
        if tform:
            points = tform.map(points)
        cx, cy = centroid(points)
        r = max([distance(cx, cy, x, y) for x, y in points])
        return r
        
    def centerAtOrigin(self):
        """Centers the trace at the origin (ignores transformations)."""
        cx, cy = centroid(self.points)
        self.points = [(x-cx, y-cy) for x,y in self.points]

    def resize(self, new_radius : float):
        """Resize a trace beased on its radius
        
            Params:
                new_radius (float): the new radius for the trace
        """
        points = self.points.copy()
        
        # calculate constants
        cx, cy = centroid(points)
        r = max([distance(cx, cy, x, y) for x, y in points])
        scale_factor = new_radius / r

        # center trace at origin and apply scale factor
        points = [
            (
                scale_factor*(x-cx) + cx, 
                scale_factor*(y-cy) + cy
            )
            for x, y in points
        ]
                
        self.points = points
    
    def addLog(self, message : str):
        """Add a log to the trace history.
        
            Params:
                message (str): the log message
        """
        self.history.append(TraceLog(message))
    
    def mergeHistory(self, other_trace):
        """Merge the history of two traces.
        
            Params:
                other_trace (Trace): the trace to merge histories with
        """
        self.history += other_trace.history
        self.history.sort()
    
    def isNew(self):
        """Returns True if the trace has no existing history."""
        return not bool(self.history)


        

