from .transform import Transform
from .trace_log import TraceLog

from modules.calc import centroid, distance
from modules.constants import blank_palette_contour

from modules.legacy_recon import (
    Contour as XMLContour,
    Transform as XMLTransform
)

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
        self.fill_mode = ("none", "none")
    
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

    def overlaps(self, other):
        """Check if trace points overlap.
        
            Params:
                other (Trace): the trace to compare
            Returns:
                (bool): whether or not trace traces overlap
        """
        if len(self.points) != len(other.points):
            return False
        
        for (x1, y1), (x2, y2) in zip(self.points, other.points):
            if abs(x1-x2) > 1e-6 or abs(y1-y2) > 1e-6:
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
        d["mode"] = self.fill_mode
        d["tags"] = list(self.tags)
        d["history"] = [list(l) for l in self.history]
        return d
    
    def getXMLObj(self, xml_image_tform : XMLTransform = None, legacy_format : bool = False):
        """Returns the trace data as an XML object.
            Params:
                xml_image_tform (XMLTransform): the xml image transform object
            Returns:
                (XMLContour) the trace as an xml contour object or (Str)
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
            mode = convertMode(self.fill_mode),
            border = border_color,
            fill = border_color,
            points = self.points,
            transform = xml_image_tform
        )

        if legacy_format:

            # get scaling to modify the radius of the trace (for palette traces)
            r_scaling = getLegacyRadius(self) / self.getRadius()
            
            xml_text = blank_palette_contour

            border = list(map(lambda x: round(x, 3), xml_contour.border))
            border = f'{border[0]} {border[1]} {border[2]}'

            fill = list(map(lambda x: round(x, 3), xml_contour.fill))
            fill = f'{fill[0]} {fill[1]} {fill[2]}'

            xml_points = ''
            for pt in xml_contour.points:
                x, y = pt[0] * r_scaling, pt[1] * r_scaling  # modify radius for palette trace
                formatted_point = f'{x} {y}, '
                xml_points += formatted_point
            
            xml_text = xml_text.replace("[NAME]", xml_contour.name)
            xml_text = xml_text.replace("[CLOSED]", str(xml_contour.closed))
            xml_text = xml_text.replace("[BORDER]", border)
            xml_text = xml_text.replace("[FILL]", fill)
            xml_text = xml_text.replace("[MODE]", str(xml_contour.mode))
            xml_text = xml_text.replace("[POINTS]", xml_points)
            
            return xml_text
        
        else:
            
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
        new_trace.fill_mode = d["mode"]
        new_trace.tags = set(d["tags"])
        new_trace.history = [TraceLog(l) for l in d["history"]]
        return new_trace
    
    # STATIC METHOD
    def fromXMLObj(xml_trace : XMLContour, xml_image_tform : XMLTransform = None, palette=False):
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
        if xml_image_tform is not None:
            points = xml_image_tform.inverseTransformPoints(points)
        
        new_trace.points = points
        new_trace.fill_mode = convertMode(xml_trace.mode)

        if not palette:
            new_trace.addLog("Imported")
        
        return new_trace

    def getBounds(self, tform : Transform = None) -> tuple:
        """Get the most extreme coordinates for the trace.
        
            Params:
                tform (Transform): optional parameter to find extremeties of transformed trace
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
    
    def getMidpoint(self, tform : Transform = None) -> tuple:
        """Get the midpoint of the trace (avg of extremes).
        
            Params:
                tform (Transform): transform to apply to calculation
            Returns:
                (tuple) x, y of midpoint
        """
        xmin, ymin, xmax, ymax = self.getBounds(tform)
        return (xmin + xmax) / 2, (ymin + ymax) / 2
    
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
    
    def magScale(self, prev_mag : float, new_mag : float):
        """Scale the trace to magnification changes.
        
            Params:
                prev_mag (float): the previous magnification
                new_mag (float): the new magnification
        """
        for i, p in enumerate(self.points):
            x, y = p
            x *= new_mag / prev_mag
            y *= new_mag / prev_mag
            self.points[i] = (x, y)
    
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

def convertMode(arg):
    """Translate between Reconstruct and PyReconstruct fill modes."""
    if type(arg) is int:
        fill_mode = [None, None]
        if abs(arg) == 11:
            fill_mode = ("none", "none")
        else:
            if abs(arg) == 13:
                fill_mode[0] = "solid"
            elif abs(arg) == 9 or abs(arg) == 15:
                fill_mode[0] = "transparent"
            if arg < 0:
                fill_mode[1] = "unselected"
            else:
                fill_mode[1] = "selected"
        return tuple(fill_mode)
    elif type(arg) is tuple or type(arg) is list:
        if arg[0] == "none":
            mode = 11
        else:
            if arg[0] == "transparent":
                mode = 9
            elif arg[0] == "solid":
                mode = 13
            if arg[1] == "unselected":
                mode *= -1
        return mode

def getLegacyRadius(trace : Trace):
    """Get the legacy radius for a palette trace."""
    legacy_radii = {
        "circle": 6.324555320336759,
        "star": 5.656854249492381,
        "triangle": 7.333333,
        "cross": 9.899494936611665,
        "square": 14.485601376004034,
        "diamond": 7,
        "curved_arrow": 12.952950706944307,
        "plus": 12.649110640673518,
        "straight_arrow": 16.646921637347848
    }
    l = len(trace.points)
    if l == 3:
        trace_type = "triangle"
    elif l == 4:
        trace_type = "diamond"
    elif l == 7:
        trace_type = "straight_arrow"
    elif l == 8:
        trace_type = "circle"
    elif l == 10:
        trace_type = "square"
    elif l == 16:
        trace_type = "star"
    elif l == 12:
        # three possibilities for length 12
        x, y = trace.points[0]
        if x < 0 and y > 0:
            if abs(abs(x) - abs(y) < 1e-6):
                trace_type = "cross"
            else:
                trace_type = "plus"
        else:
            trace_type = "curved_arrow"
    else:
        return 8
    
    return legacy_radii[trace_type]
        


        

