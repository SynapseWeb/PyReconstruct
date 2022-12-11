import numpy as np

class Transform(object):
    """ Class representing a RECONSTRUCT Transform.
    """

    def __init__(self, **kwargs):
        """ Assign instance attributes to provided args/kwargs.
        """
        # self.dim = kwargs.get("dim")
        self.xcoef = kwargs.get("xcoef")
        self.ycoef = kwargs.get("ycoef")

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
    
    def __mul__(self, other):
        """ Compose two transforms.
        """
        if self.isAffine() and other.isAffine():
            # multiply the two matrices together if both are affine
            combined_tform = np.matmul(other.tform(), self.tform())
            a = np.linalg.inv(combined_tform)
            xcoef = [a[0,2], a[0,0], a[0,1], 0, 0, 0]
            ycoef = [a[1,2], a[1,0], a[1,1], 0, 0, 0]
            return Transform(xcoef=xcoef, ycoef=ycoef)
        else:
            raise Exception("Composing polynomial transforms is not supported yet.")
    
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
    
    def tform(self):
        """ Return an np.array object of the forward tform.
        """
        if not self.isAffine():
            print("WARNING: XML transform is not affine. Truncating transform...")
        
        inverted = [[self.xcoef[1], self.xcoef[2], self.xcoef[0]],
                    [self.ycoef[1], self.ycoef[2], self.ycoef[0]],
                    [0, 0, 1]]
        forward = np.linalg.inv(np.array(inverted))
        return forward
    
    def isAffine(self):
        """ Returns True if the transform is affine.
        """
        if self.dim <= 3:
            return True
        else:
            return False

    @property
    def inverse(self):
        """ Return the inverse of the transform.
        """
        if not self.isAffine():
            print("WARNING: Inverted polynomial transforms is not supported")
        # return inverted affine matrix
        a = self.tform()
        xcoef = [a[0,2], a[0,0], a[0,1], 0, 0, 0]
        ycoef = [a[1,2], a[1,0], a[1,1], 0, 0, 0]
        return Transform(xcoef=xcoef, ycoef=ycoef)
    
    def x_forward(self, x, y):
        """Forward transform x."""
        dim = self.dim
        xcf = self.xcoef
        ycf = self.ycoef
        if dim == 0:
            result = x
        elif dim == 1:
            result = xcf[0] + x
        elif dim == 2:
            result = xcf[0] + xcf[1]*x
        elif dim == 3:
            result = xcf[0] + xcf[1]*x + xcf[2]*y
        elif dim == 4:
            result = xcf[0] + (xcf[1] + xcf[3]*y)*x + xcf[2]*y
        elif dim == 5:
            result = xcf[0] + (xcf[1] + xcf[3]*y + xcf[4]*x)*x + xcf[2]*y
        elif dim == 6:
            result = xcf[0] + (xcf[1] + xcf[3]*y + xcf[4]*x)*x + (xcf[2] + xcf[5]*y)*y 
        return result


    def y_forward(self, x, y):
        """Forward transform y."""
        dim = self.dim
        xcf = self.xcoef
        ycf = self.ycoef
        if dim == 0:
            result = y
        elif dim == 1:
            result = ycf[0] + y
        elif dim == 2:
            result = ycf[0] + ycf[1]*y
        elif dim == 3:
            result = ycf[0] + ycf[1]*x + ycf[2]*y
        elif dim == 4:
            result = ycf[0] + (ycf[1] + ycf[3]*y)*x + ycf[2]*y
        elif dim == 5:
            result = ycf[0] + (ycf[1] + ycf[3]*y + ycf[4]*x)*x + ycf[2]*y
        elif dim == 6:
            result = ycf[0] + (ycf[1] + ycf[3]*y + ycf[4]*x)*x + (ycf[2] + ycf[5]*y)*y
        return result


    def xy_forward(self, x, y):
        """Forward transform (x,y)."""
        return [self.x_forward(x, y),
                self.y_forward(x, y)]


    def xy_inverse(self, x, y):
        """Inverse transform (x, y)."""
        dim = self.dim
        xcf = self.xcoef
        ycf = self.ycoef
        epsilon = 5e-10
        if dim == 0:  # identity matrix
            pass
        elif dim == 1:  # with translation
            x = x - xcf[0]
            y = y - ycf[0]
        elif dim in [2, 3]:  # with scaling and rotation
            u = x - xcf[0]
            v = y - ycf[0]
            p = xcf[1]*ycf[2] - xcf[2]*ycf[1]
            if abs(p) > epsilon:
                x = (ycf[2]*u - xcf[2]*v)/p  # inverse of rotational part
                y = (xcf[1]*v - ycf[1]*u)/p
        elif dim in [4, 5, 6]:  # all hell breaks loose
            u, v = x, y  # (u, v) for which we want (x, y)
            x0, y0 = 0.0, 0.0  # initial (x, y) guess
            u0 = self.x_forward(x, y)  # forward t-form of initial guess
            v0 = self.y_forward(x, y)
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
                u0 = self.x_forward(x0, y0)  # forward tform of this guess
                v0 = self.y_forward(x0, y0)
                e = abs(u-u0) + abs(v-v0)  # compute closeness to goal
            x, y = x0, y0
        return [x, y]
    
    def transformPoints(self, points):
        tform_points = points.copy()
        for i in range(len(tform_points)):
            tform_points[i] = self.xy_inverse(*tform_points[i])
        return tform_points
    
    def inverseTransformPoints(self, points):
        tform_points = points.copy()
        for i in range(len(tform_points)):
            tform_points[i] = self.xy_forward(*tform_points[i])
        return tform_points
    
    def getTformList(self):
        m = self.tform()
        tform = [m[0][0], m[0][1], m[0][2], m[1][0], m[1][1], m[1][2]]
        return tform



