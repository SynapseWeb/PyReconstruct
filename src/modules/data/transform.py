import numpy as np
import cv2
from itertools import combinations

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
    
    # STATIC METHOD
    def fromQTransform(qtform : QTransform):
        """Get a Transform object from a QTransform object."""
        return Transform([
            qtform.m11(),
            qtform.m21(),
            qtform.m31(),
            qtform.m12(),
            qtform.m22(),
            qtform.m32()
        ])
    
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
        return self.tform.copy()
    
    def inverted(self):
        """Return the inverted transform.
        
            Returns:
                (Transform): the inverted transform
        """
        t, invertible = self.qtform.inverted()
        if not invertible:
            raise Exception("Matrix is not invertible")
        return Transform.fromQTransform(t)
    
    def copy(self):
        return Transform(self.tform.copy())
    
    def __mul__(self, other):
        """Compose two transforms."""
        q_composed = self.getQTransform() * other.getQTransform()
        return Transform.fromQTransform(q_composed)
    
    def magScale(self, prev_mag : float, new_mag : float):
        """Scale the transform to magnification changes.
        
            Params:
                prev_mag (float): the previous magnification
                new_mag (float): the new magnification
        """
        self.tform[2] *= new_mag / prev_mag
        self.tform[5] *= new_mag / prev_mag
    
    def estimateLinearTform(pts1, pts2):
        """Estimate the transform that converts pts1 to pts2."""
        combs = tuple(combinations(range(len(pts1)), 3))
        sum_mat = np.zeros((2, 3), dtype=np.float32)
        for c in combs:
            trip1 = [pts1[i] for i in c]
            trip2 = [pts2[i] for i in c]
            mat = cv2.getAffineTransform(
                np.array(trip1, dtype=np.float32),
                np.array(trip2, dtype=np.float32)
            )
            sum_mat += mat
        avg_mat = sum_mat / len(combs)
        tform = Transform(avg_mat.reshape(1,6).tolist()[0])

        return tform


