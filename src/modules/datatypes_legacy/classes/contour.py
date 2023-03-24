import numpy
# from shapely.geometry import LineString, Point, Polygon


class Contour(object):
    """ Class representing a RECONSTRUCT Contour.
    """

    def __init__(self, **kwargs):
        """ Apply given keyword arguments as instance attributes.
        """
        self.name = kwargs.get("name")
        self.comment = kwargs.get("comment")
        self.hidden = kwargs.get("hidden")
        self.closed = kwargs.get("closed")
        self.simplified = kwargs.get("simplified")
        self.mode = kwargs.get("mode")
        self.border = kwargs.get("border")
        self.fill = kwargs.get("fill")
        self.points = list(kwargs.get("points", []))
        # Non-RECONSTRUCT attributes
        self.transform = kwargs.get("transform")

    def __repr__(self):
        """ Return a string representation of this Contour's data.
        """
        return (
            "Contour name={name} hidden={hidden} closed={closed} "
            "simplified={simplified} border={border} fill={fill} "
            "mode={mode}\npoints={points}"
        ).format(
            name=self.name,
            hidden=self.hidden,
            closed=self.closed,
            simplified=self.simplified,
            border=self.border,
            fill=self.fill,
            mode=self.mode,
            points=self.points,
        )

    def __eq__(self, other):
        """ Allow use of == between multiple contours.
        """
        to_compare = [
            "border",
            "closed",
            "fill",
            "mode",
            "name",
            "points",
            "simplified",
            "transform",
        ]
        for k in to_compare:
            if getattr(self, k) != getattr(other, k):
                return False
        return True

    def __ne__(self, other):
        """ Allow use of != between multiple contours.
        """
        return not self.__eq__(other)

    def overlaps(self, other):
        """ Check if contour completely overlaps another in Reconstruct space.
        """
        if len(self.points) != len(other.points):
            return False
        for i in range(len(self.points)):
            self_point = self.transform.transformPoints([self.points[i]])[0]
            other_point = other.transform.transformPoints([other.points[i]])[0]
            x_neq = abs(self_point[0] - other_point[0]) > 1e-7
            y_neq = abs(self_point[1] - other_point[1]) > 1e-7
            if x_neq or y_neq:
                return False
        return True
    
    def isNegative(self):
        """Check if the trace is a negative trace."""
        if not self.closed:
            return False
        
        sum = 0
        for i in range(len(self.points)):
            x1, y1 = self.points[i-1]
            x2, y2 = self.points[i]
            sum += (x2 - x1) * (y2 + y1)
        
        return sum > 0
            
