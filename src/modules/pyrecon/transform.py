from PySide6.QtGui import QTransform

class Transform():

    def __init__(self, tform_list : list):
        """Create the transform object."""
        self.tform = tform_list
        self.qtform = self.getQTransform()
    
    def getQTransform(self):
        t = self.tform
        return QTransform(t[0], t[3], t[1], t[4], t[2], t[5])
    
    def imageTransform(self):
        t = self.tform
        return Transform([t[0], -t[1], 0, -t[3], t[4], 0])
    
    def map(self, *args, inverted=False):
        """Apply the transform to a single point or a list of points."""
        if inverted:
            qtform, invertible = self.qtform.inverted()
            if not invertible:
                raise Exception("Matrix is not invertible.")
        else:
            qtform = self.qtform
        if len(args) == 2:
            return qtform.map(args[0], args[1])
        elif len(args) == 1:
            return [qtform.map(*p) for p in args[0]]
    
    def getList(self):
        """Get the tform list numbers."""
        return self.tform
    
    def inverted(self):
        """Return the inverted transform."""
        t, invertible = self.qtform.inverted()
        if not invertible:
            raise Exception("Matrix is not invertible")
        return Transform([
            t.m11(),
            t.m21(),
            t.m31(),
            t.m12(),
            t.m22(),
            t.m32()
        ])
    
    def copy(self):
        return Transform(self.tform.copy())

