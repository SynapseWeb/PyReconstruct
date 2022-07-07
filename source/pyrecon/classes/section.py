class Section(object):
    """ Class representing a RECONSTRUCT Section.
    """

    def __init__(self, **kwargs):
        """ Apply given keyword arguments as instance attributes.
        """
        self.name = kwargs.get("name")  # Series name + "." + index
        self.index = kwargs.get("index")
        self.thickness = kwargs.get("thickness")
        self.alignLocked = kwargs.get("alignLocked")
        # Non-attributes
        self.images = kwargs.get("images", [])  # TODO: d1fixed
        self.contours = kwargs.get("contours", [])
        self._path = kwargs.get("_path")

# ACCESSORS
    def __len__(self):
        """ Return number of contours in Section object.
        """
        return len(self.contours)

    def __eq__(self, other):  # TODO: images eval correctly?
        """ Allow use of == between multiple objects.
        """
        return (self.thickness == other.thickness and
                self.index == other.thickness and
                self.alignLocked == other.alignLocked and
                self.images == other.images and  # TODO: d1fixed
                self.contours == other.contours)

    def __ne__(self, other):
        """ Allow use of != between multiple objects.
        """
        return not self.__eq__(other)

    def eq(self, other, eq_type=None):  # TODO
        """ Check equivalency with the option for type of attributes
            to compare.

            Default: __eq__
        """
        if not eq_type:
            return self.__eq__(other)
        elif eq_type.lower() == 'attributes':
            return (self.thickness == other.thickness and
                    self.index == other.index and
                    self.alignLocked == other.alignLocked)
        elif eq_type.lower() in ['images', 'image', 'img']:
            return (self.images == other.images)  # TODO: d1fixed
        elif eq_type.lower() in ['contours', 'contour']:
            return (self.contours == other.contours)

    def attributes(self):
        """ Return a dict of this Section's attributes.
        """
        return {
            "name": self.name,
            "index": self.index,
            "thickness": self.thickness,
            "alignLocked": self.alignLocked
        }
    
    def transformAllContours(self, tform, reverse=False):
        """Transform all traces on a single section.
        """
        for contour in self.contours:
            if not reverse:
                contour.transform = contour.transform * tform
            else:
                contour.transform = tform * contour.transform
        
    def transformAllImages(self, tform, reverse=False):
        """Transform/translate all the images for a single section.
        """
        for image in self.images:
            if not reverse:
                image.transform = image.transform * tform
            else:
                image.transform = tform * image.transform
            