from PySide6.QtGui import QTransform

class Transform():

    def __init__(self, tform_list : list):
        """Create the transform object.
        
            Params:
                tform_list (list): the tform as a six-number list
        """
        self.tform = tform_list
        self.qtform = self.getQTransform()
    
    def getQTransform(self) -> QTransform:
        """Get the transform as a QTransform object.
        
            Returns:
                (QTransform): the QTransform object
        """
        t = self.tform
        return QTransform(t[0], t[3], t[1], t[4], t[2], t[5])
    
    def imageTransform(self):
        """Get the transform object as it should apply to images.
        
            Returns:
                (Transform): the image-style transform
        """
        t = self.tform
        return Transform([t[0], -t[1], 0, -t[3], t[4], 0])
    
    def map(self, *args, inverted=False):
        """Apply the transform to a single point or a list of points.
        
            Params:
                (tuple): an x, y coordinate pair to transform
                OR
                (list): a list of points to transform
            Returns:
                (tuple) OR (list): the transformed point or points
        """
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
    
    def getList(self) -> list:
        """Get the tform list numbers.
        
            Returns:
                (list): the six-number transform
        """
        return self.tform
    
    def inverted(self):
        """Return the inverted transform.
        
            Returns:
                (Transform): the inverted transform
        """
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

