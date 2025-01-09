from typing import Union

from skimage.draw import polygon
import numpy as np

from .transform import Transform
from .points import Points

from PyReconstruct.modules.calc import centroid, distance, feret
from PyReconstruct.modules.constants import blank_palette_contour
from PyReconstruct.modules.calc import point_list_2_pix

from PyReconstruct.modules.datatypes_legacy import (
    Contour as XMLContour,
    Transform as XMLTransform
)


class Trace():

    def __init__(self, name : str, color : tuple, closed=True):
        """Create a Trace object.
        
            Params:
                name (str): the name of the trace
                color (tuple): the color of the trace: (R, G, B) 0-255
                closed (bool): True if trace is closed
        """
        self.name       = name
        self.color      = color
        self.closed     = closed
        self.negative   = False
        self.points     = []
        self.hidden     = False
        self.tags       = set()
        self.fill_mode  = ("none", "none")
    
    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        """Replace whitespace and commas with underscores."""
        
        assert (value is None or type(value) is str)

        if value is not None:
            
            value = value.strip()
            value = "_".join(value.split()).replace(",", "_")
            
        self._name = value
    
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
                point (tuple): a coordinate pair
        """
        self.points.append(point)
    
    def asPixels(self, mag: float, img_height: int):
        """Return points as a list of (x, y) pixels on an image."""

        return point_list_2_pix(self.points, mag, img_height)

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

    def overlaps(self, other, threshold=0.99):
        """Check if trace points overlap.
        
            Params:
                other (Trace): the trace to compare
                threshold (float): the threshold overlap ratio to define overlapping (exclusive)
            Returns:
                (bool): whether or not trace traces overlap
        """
        if self.closed != other.closed:
            return False
        
        # compare points directly
        points_match = True
        if len(self.points) != len(other.points):
            points_match = False
        else:      
            for (x1, y1), (x2, y2) in zip(self.points, other.points):
                if abs(x1-x2) > 1e-2 or abs(y1-y2) > 1e-2:
                    points_match = False
                    break
        if points_match:
            return True
        
        # compare amount of overlap
        r = self.getOverlapRatio(other)
        if threshold < 1 and r > threshold:
            return True
        elif threshold == r == 1:
            return True
        else:
            return False
    
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
        self.tags.add(tag)

    def getList(self, include_name=True) -> dict:
        """Return the trace data as a dictionary.
        
            Params:
                include_name (bool): True if name should be included in dict
            Returns:
                (list) list containing the trace data
        """
        x, y = [], []
        for p in self.points:
            x.append(round(p[0], 7))
            y.append(round(p[1], 7))
        
        l = []
        if include_name:
            l.append(self.name)
        
        l += [
            x, 
            y, 
            self.color,
            self.closed,
            self.negative,
            self.hidden,
            self.fill_mode,
            list(self.tags)
        ]

        return l
    
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

        # reverse point order if negative trace
        if self.negative:
            points = self.points[::-1]
        else:
            points = self.points

        xml_contour = XMLContour(
            name = self.name,
            comment = "",
            hidden = self.hidden,
            closed = self.closed,
            simplified = False,
            mode = convertMode(self.fill_mode),
            border = border_color,
            fill = border_color,
            points = points,
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
    
    @staticmethod
    def fromList(l : list, name : str = None):
        """Create a trace object from a dictionary.
        
            Params:
                list (dict): the list trace data
                name (str): the name of the trace
            Returns:
                (Trace) a Trace object constructed from the dictionary data
        """

        if not name or len(l) == 9:
            name = l.pop(0)
        
        (
            x,
            y,
            color,
            closed,
            negative,
            hidden,
            fill_mode,
            tags
        ) = tuple(l)

        new_trace = Trace(name.strip(), color, closed)  # strip trace name
        new_trace.negative = negative
        new_trace.points = list(zip(x, y))
        new_trace.hidden = hidden
        new_trace.fill_mode = fill_mode
        new_trace.tags = set(tags)

        return new_trace
    
    @staticmethod
    def fromXMLObj(xml_trace : XMLContour, xml_image_tform : XMLTransform = None):
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
        negative = xml_trace.isNegative()
        if negative:
            points = points[::-1]
        new_trace = Trace(name, color, closed)

        # get the transform
        if xml_trace.transform is not None:
            points = xml_trace.transform.transformPoints(xml_trace.points)
        if xml_image_tform is not None:
            points = xml_image_tform.inverseTransformPoints(points)
        
        new_trace.points = points
        new_trace.fill_mode = convertMode(xml_trace.mode)
        new_trace.negative = negative
        
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
        if tform is not None:
            points = tform.map(self.points)
        else:
            points = self.points.copy()

        xmin = xmax = points[0][0]  # BUG: Should this be 'points' and not 'self.points'?
        ymin = ymax = points[0][1]
        
        for x, y in points[1:]:
            if x < xmin: xmin = x
            elif x > xmax: xmax = x
            if y < ymin: ymin = y
            elif y > ymax: ymax = y
        
        return xmin, ymin, xmax, ymax
    
    def getMidpoint(self, tform : Transform = None) -> tuple:
        """Get the midpoint of the trace (avg of extremes).
        
            Params:
                tform (Transform): transform to apply to calculation
            Returns:
                (tuple) x, y of midpoint
        """
        xmin, ymin, xmax, ymax = self.getBounds(tform)
        return (xmin + xmax) / 2, (ymin + ymax) / 2

    def getCentroid(self, tform : Transform = None) -> tuple:
        """Get the centroid of the trace.
        
            Params:
                tform (Transform)"""
        c = centroid(self.points)
        if tform:
            return tform.map(*c)
        else:
            return c
    
    def getRadius(self, tform : Transform = None) -> float:
        """Get the distance from the centroid of the trace to its farthest point.
        
            Params:
                tform (Transform): the transform to apply to the points
            Returns:
                (float): the radius of the trace
        """
        points = self.points.copy()
        if tform:
            points = tform.map(points)
        cx, cy = centroid(points)
        r = max([distance(cx, cy, x, y) for x, y in points])
        return r

    def getFeret(self, tform : Transform = None) -> float:
        """Get min and max Feret diameters.
        
            Params:
                tform (Transform): the transform to apply to the points
            Returns:
                (float): the radius of the trace
        """

        if not self.closed:  # no feret diameter for open traces
            
            return (0,0)

        else:
        
            points = self.points.copy()
        
            if tform:
                points = tform.map(points)
            
            return feret(points)

    def centerAtOrigin(self):
        """Centers the trace at the origin (ignores transformations)."""
        cx, cy = centroid(self.points)
        self.points = [(x-cx, y-cy) for x,y in self.points]

    def resize(self, new_radius : float, tform : Transform = None):
        """Resize a trace beased on its radius
        
            Params:
                new_radius (float): the new radius for the trace
                tform (Transform): the transform to apply to the radius
        """
        points = self.points.copy()

        # apply the forward transform if applicable
        if tform:
            points = tform.map(points)
        
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

        # apply the reverse transform if applicable
        if tform:
            points = tform.map(points, inverted=True)
                
        self.points = points

    def reshape(self, new_points : float, tform : Transform = None):
        """Resize a trace beased on its radius
        
            Params:
                new_points (float): the new points for the trace
                tform (Transform): the transform to apply the shape
        """
        r = self.getRadius(tform)
        xc, yc = self.getCentroid()

        self.points = new_points
        self.resize(r)
        # apply reverse transform if applicable
        if tform:
            self.points = tform.getLinear().map(self.points, inverted=True)

        self.points = [(x + xc, y + yc) for x, y in self.points]
    
    def getStretched(self, w : float, h : float):
        """Get the trace stretched to a specific w and h.
        
            Params:
                w (float): the width of the resulting trace
                h (float): the height of the resulting trace
            Returns:
                (Trace): the resulting trace
        """
        new_trace = self.copy()

        # get constants
        cx, cy = centroid(new_trace.points)
        xmin, ymin, xmax, ymax = self.getBounds()

        # get scale factors
        scale_x = w / (xmax - xmin)
        scale_y = h / (ymax - ymin)

        # center trace at origin and apply scale factor
        new_trace.points = [
            (
                scale_x*(x-cx) + cx, 
                scale_y*(y-cy) + cy
            )
            for x, y in new_trace.points
        ]
        
        return new_trace
    
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

    def mergeTags(self, other):
        """Merge the tags of two traces.
        
            Params:
                other (Trace): the trace to merge tags with
        """
        self.tags = self.tags.union(other.tags)
    
    def getOverlapRatio(self, other):
        """Get the amount of intersection between two traces.
        
            Params:
                other (Trace): the trace to compare against
        """
        xmin1, ymin1, xmax1, ymax1 = self.getBounds()
        xmin2, ymin2, xmax2, ymax2 = other.getBounds()

        # if the shapes don't remotely intersect, ignore
        if (
            xmax1 < xmin2 or xmax2 < xmin1 or
            ymax1 < ymin2 or ymax2 < ymin1):
            return 0
        
        pts1 = np.array(self.points)
        pts2 = np.array(other.points)
        
        # calculate a scaling factor
        xmin, xmax = min(xmin1, xmin2), max(xmax1, xmax2)
        ymin, ymax = min(ymin1, ymin2), max(ymax1, ymax2)
        initial_area = (xmax-xmin) * (ymax-ymin)
        scale_factor = (1e4 / initial_area) ** 0.5

        # scale the points
        pts1 = np.round(pts1 * scale_factor).astype(int)
        pts2 = np.round(pts2 * scale_factor).astype(int)
        xmin = round(xmin * scale_factor)
        xmax = round(xmax * scale_factor)
        ymin = round(ymin * scale_factor)
        ymax = round(ymax * scale_factor)

        # translate the points
        pts1[:,0] -= xmin
        pts1[:,1] -= ymin
        pts2[:,0] -= xmin
        pts2[:,1] -= ymin

        # generate the polygons
        r1, c1 = polygon(pts1[:,1], pts1[:,0])
        r2, c2 = polygon(pts2[:,1], pts2[:,0])
        mask1 = np.zeros(shape=(ymax-ymin+1, xmax-xmin+1), dtype=bool)
        mask2 = np.zeros(shape=(ymax-ymin+1, xmax-xmin+1), dtype=bool)
        mask1[r1, c1] = True
        mask2[r2, c2] = True

        # get the union and intersect areas
        union_area = np.sum(np.logical_or(mask1, mask2))
        intersect_area = np.sum(np.logical_and(mask1, mask2))

        return intersect_area / union_area

    def smooth(self, window: int, spacing: Union[int, float]) -> None:
        """Smooth trace."""

        unsmoothed = Points(self.points, self.closed)

        smoothed = unsmoothed.interp_rolling_average(
            spacing, window, as_int=False
        )

        if smoothed[0] == smoothed[-1]:

            smoothed = smoothed[:-1]

        self.points = smoothed
    
    @staticmethod
    def get_scale_bar():
        """Return a scale bar trace object."""

        ## Initialize trace
        scale_bar_trace = Trace("scale_bar", color=(0, 0, 0))

        ## Add attrs
        scale_bar_trace.points = [
            (0, 0), (0, 0.2), (2, 0.2), (2, 0)
        ]
        scale_bar_trace.fill_mode = ("solid", "always")

        return scale_bar_trace


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
