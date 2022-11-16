from PySide6.QtGui import QTransform

class Transform():

    def __init__(self, tform_list : list):
        """Create the transform object."""
        self.tform = tform_list
        self.qtform = self.getQTransform()
    
    def getQTransform(self):
        t = self.tform
        return QTransform(t[0], t[3], t[1], t[4], t[2], t[5])
    
    def map(self, *args):
        """Apply the transform to a single point or a list of points."""
        if len(args) == 2:
            return self.qtform.map(args[0], args[1])
        elif len(args) == 1:
            return [self.qtform.map(*p) for p in args[0]]