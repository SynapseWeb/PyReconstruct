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
                mode (int): the display mode of the trace (XML use)
        """
        self.name = name
        self.color = color
        self.closed = closed
        self.points = []
        self.hidden = False  # default to False
        self.tags = set()

        # extra hidden attributes for XML support
        self.comment = None
        self.simplified = None
        self.mode = 11
        self.fill = tuple([c / 255 for c in self.color])
    
    def copy(self):
        """Create a copy of the trace object.
        
            Returns:
                (Trace): a copy of the object
        """
        copy_trace = Trace("", [0,0,0])
        copy_trace.__dict__ = self.__dict__.copy()
        copy_trace.points = self.points.copy()
        copy_trace.tags = self.tags.copy()
        return copy_trace
    
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
    
    def addTag(self, tag : str):
        """Set the tag for the trace:
            
            Params:
                tag (str): the tag for the trace
        """
        self.tags.append(tag)

    def getDict(self) -> dict:
        """Return the trace data as a dictionary.
        
            Returns:
                (dict) dictionary containing the trace data
        """
        d = {}
        d["name"] = self.name
        d["color"] = self.color
        d["closed"] = self.closed
        d["points"] = self.points
        d["hidden"] = self.hidden
        d["tags"] = list(self.tags)
        return d
    
    def getXMLObj(self, xml_image_tform : XMLTransform = None) -> XMLContour:
        """Returns the trace data as an XML object.
            Params:
                xml_image_tform (XMLTransform): the xml image transform object
            Returns:
                (XMLContour) the trace as an xml contour object
        """
        border_color = list(self.color.copy())
        for i in range(len(border_color)):
            border_color[i] /= 255
        xml_contour = XMLContour(
            name = self.name,
            comment = self.comment,
            hidden = self.hidden,
            closed = self.closed,
            simplified = self.simplified,
            mode = self.mode,
            border = border_color,
            fill = self.fill,
            points = self.points,
            transform = xml_image_tform
        )
        return xml_contour
    
    # STATIC METHOD
    def fromDict(d):
        """Create a trace object from a dictionary.
        
            Params:
                d (dict): the dictionary contour data
            Returns:
                (Trace) a Trace object constructed from the dictionary data
        """
        new_trace = Trace(d["name"], d["color"], d["closed"])
        new_trace.points = d["points"]
        new_trace.hidden = d["hidden"]
        new_trace.tags = set(d["tags"])
        return new_trace
    
    # STATIC METHOD
    def fromXMLObj(xml_trace : XMLContour, xml_image_tform : XMLTransform = None):
        """Create a trace from an xml contour object.
        
            Params:
                xml_trace (XMLContour): the xml contour object
                xml_image_tform (XMLTransform): the xml image transform object
            Returns:
                (Trace) the trace object
        """
        name = xml_trace.name
        color = list(xml_trace.border)
        for i in range(len(color)):
            color[i] = int(color[i] * 255)
        closed = xml_trace.closed
        points = xml_trace.points.copy()
        if xml_trace.transform is not None:
            points = xml_trace.transform.transformPoints(xml_trace.points)
        if xml_image_tform is not None:
            points = xml_image_tform.inverseTransformPoints(points)
        new_trace = Trace(name, color, closed)
        new_trace.points = points

        # store extra attributes for traces from xml files
        new_trace.comment = xml_trace.comment
        new_trace.simplified = xml_trace.simplified
        new_trace.mode = xml_trace.mode
        new_trace.fill = xml_trace.fill

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
    
    def getRadius(self, tform=None):
        """Get the distance from the centroid of the trace to its farthest point.
        
            Params:
                tform: the transform to apply to the points
        """
        points = self.points.copy()
        if tform:
            points = [tform.map(*p) for p in self.points]
        cx, cy = centroid(points)
        r = max([distance(cx, cy, x, y) for x, y in points])
        return r
        
    def centerAtOrigin(self):
        """Centers the trace at the origin (ignores transformations)."""
        cx, cy = centroid(self.points)
        self.points = [(x-cx, y-cy) for x,y in self.points]

    def resize(self, new_radius, tform=None):
        """Resize a trace beased on its radius
        
            Params:
                new_radius: the new radius for the trace
                tform: the tform applied to the trace
        """
        points = self.points.copy()
        if tform:
            points = [tform.map(*p) for p in self.points]
        
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

        # restore untransformed version
        if tform:
            points = [tform.inverted()[0].map(*p) for p in points]
        
        self.points = points


        

