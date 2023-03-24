class Image(object):
    """ Class representing a RECONSTRUCT Image.
    """

    def __init__(self, **kwargs):
        """ Apply given keyword arguments as instance attributes.
        """
        self.src = kwargs.get("src")
        self.mag = kwargs.get("mag")
        self.contrast = kwargs.get("contrast")
        self.brightness = kwargs.get("brightness")
        self.red = kwargs.get("red")
        self.green = kwargs.get("green")
        self.blue = kwargs.get("blue")
        self.transform = kwargs.get("transform")

        # RECONSTRUCT has a Contour for Images
        self.name = kwargs.get("name")
        self.hidden = kwargs.get("hidden")
        self.closed = kwargs.get("closed")
        self.simplified = kwargs.get("simplified")
        self.border = kwargs.get("border")
        self.fill = kwargs.get("fill")
        self.mode = kwargs.get("mode")
        self.points = list(kwargs.get("points", []))

        # Metadata
        self._path = kwargs.get("_path")

    def __eq__(self, other):
        """ Allow use of == operator.
        """
        return (
            self.src == other.src and
            self.brightness == other.brightness and
            self.contrast == other.contrast and
            self.name == other.name and
            self.closed == other.closed and
            self.simplified == other.simplified and
            self.border == other.border and
            self.fill == other.fill and
            self.mode == other.mode and
            self.points == other.points
        )

    def __ne__(self, other):
        """ Allow use of != operator.
        """
        return not self.__eq__(other)

    def attributes(self):
        """ Return relevent attributes as dict.
        """
        return {
            "src": self.src,
            "mag": self.mag,
            "contrast": self.contrast,
            "brightness": self.brightness,
            "path": self._path or "" + self.src
        }
