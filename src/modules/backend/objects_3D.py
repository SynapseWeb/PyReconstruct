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
        surf = pdata.delaunay_3d(alpha=0.1, progress_bar=True).extract_surface()
        
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
