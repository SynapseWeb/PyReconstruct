import cv2

import numpy as np

import pyqtgraph.opengl as gl

from pyvista.core.pointset import PolyData

from modules.calc.quantification import centroid

from modules.pyrecon.trace import Trace
from modules.pyrecon.transform import Transform

class Object3D():

    def __init__(self, name):
        self.name = name
        self.extremes = []  # xmin, xmax, ymin, ymax, zmin, zmax
    
    def addToExtremes(self, x, y, z):
        """Keep track of the extreme values."""
        if not self.extremes:
            self.extremes = [x, x, y, y, z, z]
        else:
            if x < self.extremes[0]: self.extremes[0] = x
            if x > self.extremes[1]: self.extremes[1] = x
            if y < self.extremes[2]: self.extremes[2] = y
            if y > self.extremes[3]: self.extremes[3] = y
            if z < self.extremes[4]: self.extremes[4] = z
            if z > self.extremes[5]: self.extremes[5] = z

class Surface(Object3D):

    def __init__(self, name):
        """Create a 3D Surface object."""
        super().__init__(name)
        self.color = None
        self.point_cloud = []
    
    def addTrace(self, trace : Trace, z : float, tform : Transform = None):
        """Add a trace to the surface data."""
        if not self.color:
            self.color = tuple([c/255 for c in trace.color])
        
        for pt in trace.points:
            if tform:
                x, y = tform.map(*pt)
            else:
                x, y = pt
            self.point_cloud.append((x, y, z))
            self.addToExtremes(x, y, z)
    
    def generate3D(self, alpha=1):
        """Generate the opengl mesh."""
        # use pyvista to generate the faces
        pdata = PolyData(np.array(self.point_cloud))
        surf = pdata.delaunay_3d(alpha=0.1).extract_surface()
        
        # extract face data
        verts = surf.points
        faces = surf.faces.reshape((int(surf.faces.shape[0]/4), 4))
        faces = faces[:, 1:]

        # create object
        item = gl.GLMeshItem(
                vertexes=verts,
                faces=faces,
                color=(*self.color, alpha),
                shader="edgeDarken",
                glOptions="translucent",
                smooth=True
        )

        return item

class Spheres(Object3D):

    def __init__(self, name):
        """Create a 3D Spheres object."""
        super().__init__(name)
        self.colors = []
        self.centroids = []
        self.radii = []
    
    def addTrace(self, trace : Trace, z : float, tform : Transform = None):
        """Add a trace to the spheres data."""
        self.colors.append(tuple([c/255 for c in trace.color]))

        x, y = centroid(trace.points)
        if tform:
            x, y = tform.map(x, y)
        self.centroids.append((x, y, z))
        self.addToExtremes(x, y, z)

        self.radii.append(trace.getRadius(tform))
    
    def generate3D(self, alpha=1):
        """Generate the opengl meshes for the spheres."""
        items = []
        for color, point, radius in zip(
            self.colors,
            self.centroids,
            self.radii
        ):
            sphere = gl.MeshData.sphere(rows=6, cols=6, radius=radius)
            item = gl.GLMeshItem(
                meshdata=sphere,
                smooth=True,
                color=(*color, alpha),
                shader="edgeDarken",
                glOptions="translucent",
            )
            item.translate(*point)
            items.append(item)
        
        return items

class Voxels(Object3D):

    def __init__(self, name):
        """Create a voxels object."""
        super().__init__(name)
        self.traces = []
        self.snums = []
        self.closed = []
        self.colors = []
        self.sts = {}  # section thicknesses
        self.smin = None
        self.smax = None
    
    def addToExtremes(self, x, y, z, snum):
        super().addToExtremes(x, y, z)
        if self.smin is None or snum < self.smin:
            self.smin = snum
        if self.smax is None or snum > self.smax:
            self.smax = snum
    
    def addTrace(self, trace : Trace, snum : int, z : float, thickness : float, tform : Transform = None):
        """Add a trace to the voxels data."""
        poly = []
        for pt in trace.points:
            if tform:
                x, y = tform.map(*pt)
            else:
                x, y = pt
            poly.append((x, y, snum))
            self.addToExtremes(x, y, z, snum)
        self.traces.append(poly)

        self.snums.append(snum)

        self.closed.append(trace.closed)

        self.colors.append(trace.color)

        self.sts[snum] = thickness

    def generate3D(self, mag : float, alpha=1):
        """Genrate the opengl volume."""
        # get the average section thickness
        # ASSUMES ALL SECTIONS HAVE RELATIVELY SIMILAR THICKNESS
        avg_thickness = sum(list(self.sts.values())) / len(self.sts)

        xmin, xmax, ymin, ymax, zmin, zmax = tuple(self.extremes)

        volume = np.zeros(
            (
                int((xmax-xmin) / mag) + 1,
                int((ymax-ymin) / mag) + 1,
                self.smax-self.smin + 1,
                4
            ),
            dtype=np.uint8
        )

        for trace, snum, closed, color in zip(
            self.traces,
            self.snums,
            self.closed,
            self.colors
        ):
            pts = np.array(trace)
            pts[:,0] -= xmin
            pts[:,1] -= ymin
            pts /= mag
            pts = pts.astype(np.int32)

            if closed:
                cv2.fillPoly(
                    img=volume[:,:,snum],
                    pts=[pts],
                    color=(*color, int(alpha*255))
                )
            else:
                cv2.polylines(
                    img=volume[:,:,snum],
                    pts=[pts],
                    isClosed=False,
                    color=(*color, int(alpha*255))
                )
            
        item = gl.GLVolumeItem(volume)

        item.scale(mag, mag, avg_thickness)
        item.translate(xmin, ymin, zmin)
        
        return item