import numpy as np

class Transform(object):
    """ Class representing a RECONSTRUCT Transform.
    """
    # STATIC METHOD
    def getTranslateTransform(xshift, yshift):
        """Return a transform for the given translation"""
        return Transform(xcoef=[-xshift,1,0,0,0,0], ycoef=[-yshift,0,1,0,0,0])

    def __init__(self, **kwargs):
        """ Assign instance attributes to provided args/kwargs.
        """
        # self.dim = kwargs.get("dim")
        self.xcoef = kwargs.get("xcoef")
        self.ycoef = kwargs.get("ycoef")
    
    @property
    def dim(self):
        if self.xcoef == [0,1,0,0,0,0] and self.ycoef == [0,0,1,0,0,0]:
            return 0
        elif self.xcoef[1:] == [1,0,0,0,0] and self.ycoef[1:] == [0,1,0,0,0]:
            return 1
        else:
            xcheck = self.xcoef[3:]
            ycheck = self.ycoef[3:]
            for elem in xcheck:
                if elem != 0:
                    return 6
            for elem in ycheck:
                if elem != 0:
                    return 6
            return 3

    @property
    def _tform(self):
        """ Return an np.array object of the forward tform.
        """
        if self.isAffine():
            inverted = [[self.xcoef[1], self.xcoef[2], self.xcoef[0]],
                        [self.ycoef[1], self.ycoef[2], self.ycoef[0]],
                        [0, 0, 1]]
            forward = np.linalg.inv(np.array(inverted))
            return forward

    def __eq__(self, other):
        """ Allow use of == operator.
        """
        to_compare = ["xcoef", "ycoef"]
        for k in to_compare:
            if getattr(self, k) != getattr(other, k):
                return False
        return True

    def __ne__(self, other):
        """ Allow use of != operator.
        """
        return not self.__eq__(other)
    
    def isAffine(self):
        """ Returns True if the transform is affine.
        """
        xcheck = self.xcoef[3:6]
        ycheck = self.ycoef[3:6]
        for elem in xcheck:
            if elem != 0:
                return False
        for elem in ycheck:
            if elem != 0:
                return False
        return True
    
    def __mul__(self, other):
        """ Compose two transforms.
        """
        if self.isAffine() and other.isAffine():
            # multiply the two matrices together if both are affine
            combined_tform = np.matmul(other._tform, self._tform)
            a = np.linalg.inv(combined_tform)
            xcoef = [a[0,2], a[0,0], a[0,1], 0, 0, 0]
            ycoef = [a[1,2], a[1,0], a[1,1], 0, 0, 0]
            return Transform(xcoef=xcoef, ycoef=ycoef)
        else:
            raise Exception("Composing polynomial transforms is not supported yet.")

    @property
    def inverse(self):
        """ Return the inverse of the transform.
        """
        if self.isAffine():
            # return inverted matrix if affine
            a = self._tform
            xcoef = [a[0,2], a[0,0], a[0,1], 0, 0, 0]
            ycoef = [a[1,2], a[1,0], a[1,1], 0, 0, 0]
            return Transform(xcoef=xcoef, ycoef=ycoef)
        else:
            raise Exception("Inverting polynomial transforms is not supported yet.")

    def transformPoints(self, pts):
        """ Transform a list of points.
        """
        tform_points = []
        if self.isAffine():
            forward_tform = self._tform
            for point in pts:
                point_mat = np.array([[point[0]],[point[1]],[1]])
                tform_point_mat = np.matmul(forward_tform, point_mat)
                tform_point = (tform_point_mat[0][0], tform_point_mat[1][0])
                tform_points.append(tform_point)
        else:
            for point in pts:
                x = point[0]
                y = point[1]
                # Michael's Code!
                xcf = self.xcoef
                ycf = self.ycoef
                epsilon = 5e-10
                u, v = x, y  # (u, v) for which we want (x, y)
                x0, y0 = 0.0, 0.0  # initial (x, y) guess
                u0 = xcf[0] + (xcf[1] + xcf[3]*y + xcf[4]*x)*x + (xcf[2] + xcf[5]*y)*y # forward t-form of initial guess
                v0 = ycf[0] + (ycf[1] + ycf[3]*y + ycf[4]*x)*x + (ycf[2] + ycf[5]*y)*y
                i = 0  # allow no more than 10 iterations
                e = 1.0  # to reduce error to this limit
                while e > epsilon and i < 10:
                    i += 1
                    l = xcf[1] + xcf[3]*y0 + 2.0*xcf[4]*x0  # compute Jacobian
                    m = xcf[2] + xcf[3]*x0 + 2.0*xcf[5]*y0
                    n = ycf[1] + ycf[3]*y0 + 2.0*ycf[4]*x0
                    o = ycf[2] + ycf[3]*x0 + 2.0*ycf[5]*y0
                    p = l*o - m*n  # determinant for inverse
                    if abs(p) > epsilon:
                        x0 += (o*(u-u0) - m*(v-v0))/p  # inverse of Jacobian
                        y0 += (l*(v-v0) - n*(u-u0))/p  # and use to increment (x0, y0)
                    else:
                        x0 += l*(u-u0) + n*(v-v0)  # try Jacobian transpose instead
                        y0 += m*(u-u0) + o*(v-v0)
                    u0 = xcf[0] + (xcf[1] + xcf[3]*y + xcf[4]*x)*x + (xcf[2] + xcf[5]*y)*y   # forward tform of this guess
                    v0 = ycf[0] + (ycf[1] + ycf[3]*y + ycf[4]*x)*x + (ycf[2] + ycf[5]*y)*y
                    e = abs(u-u0) + abs(v-v0)  # compute closeness to goal
                tform_points.append((x0, y0))
        return tform_points
