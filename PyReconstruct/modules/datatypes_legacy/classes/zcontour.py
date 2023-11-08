import numpy
# from shapely.geometry import LineString, Polygon


class ZContour(object):
    """ Class representing a RECONSTRUCT ZContour.
    """

    def __init__(self, **kwargs):
        """ Assign instance attributes from args/kwargs.
        """
        self.name = kwargs.get("name")
        self.closed = kwargs.get("closed")
        self.border = kwargs.get("border")
        self.fill = kwargs.get("fill")
        self.mode = kwargs.get("mode")
        self.points = kwargs.get("points", [])

    def __eq__(self, other):
        """ Allow use of == operator.
        """
        to_compare = ["name", "points", "closed"]
        for k in to_compare:
            if getattr(self, k) != getattr(other, k):
                return False
        return True

    def __ne__(self, other):
        """ Allow use of != operator.
        """
        return not self.__eq__(other)

##    @property
##   def shape(self):
##        """ Return a Shapely geometric object.
##        """
##        if not self.points:
##            raise Exception("No points found: {}".format(self))
##
##        array = numpy.asarray(self.points)
##
##        # Normalize points
##        if len(array) == 2:
##            return LineString(array)
##        return Polygon(array)
