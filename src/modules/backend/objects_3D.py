import numpy as np

import pyqtgraph.opengl as gl

from skimage.draw import polygon
import trimesh

from modules.calc.quantification import centroid

from modules.pyrecon.trace import Trace
from modules.pyrecon.transform import Transform

class Object3D():

    def __init__(self, name):
        self.name = name
        self.extremes = []  # xmin, xmax, ymin, ymax, zmin, zmax
    
    def addToExtremes(self, x, y, s):
        """Keep track of the extreme values."""
        if not self.extremes:
            self.extremes = [x, x, y, y, s, s]
        else:
            if x < self.extremes[0]: self.extremes[0] = x
            if x > self.extremes[1]: self.extremes[1] = x
            if y < self.extremes[2]: self.extremes[2] = y
            if y > self.extremes[3]: self.extremes[3] = y
            if s < self.extremes[4]: self.extremes[4] = s
            if s > self.extremes[5]: self.extremes[5] = s

class Surface(Object3D):

    def __init__(self, name):
        """Create a 3D Surface object."""
        super().__init__(name)
        self.color = None
        self.traces = {}
    
    def addTrace(self, trace : Trace, snum : int, tform : Transform = None):
        """Add a trace to the surface data."""
        if self.color is None:
            self.color = tuple([c/255 for c in trace.color])
        
        if snum not in self.traces:
            self.traces[snum] = []
        
        pts = []
        for pt in trace.points:
            if tform:
                x, y = tform.map(*pt)
            else:
                x, y = pt
            self.addToExtremes(x, y, snum)
            pts.append((x, y))
        
        self.traces[snum].append(pts)
    
    def generate3D(self, section_mag, section_thickness, alpha=1):
        """Generate the numpy array volumes.
        """
        # set mag to four times average sections mag
        mag = section_mag * 8

        # calculate the dimensions of the volume
        xmin, xmax, ymin, ymax, smin, smax = tuple(self.extremes)
        vshape = (
            smax-smin+1,
            round((ymax-ymin)/mag)+1,
            round((xmax-xmin)/mag)+1
        )
    
        # create the numpy volume
        volume = np.zeros(vshape, dtype=bool)

        # add the traces to the volume
        for snum, trace_list in self.traces.items():
            for trace in trace_list:
                x_values = []
                y_values = []
                for x, y in trace:
                    x_values.append(round((x-xmin) / mag))
                    y_values.append(round((y-ymin) / mag))
                y_pos, x_pos = polygon(
                    np.array(y_values),
                    np.array(x_values)
                )
                volume[snum - smin, y_pos, x_pos] = True

        # generate and smooth the trimesh
        tm = trimesh.voxel.ops.matrix_to_marching_cubes(volume)
        # trimesh.smoothing.filter_humphrey(tm)
        trimesh.smoothing.filter_laplacian(tm)

        faces = tm.faces
        verts = tm.vertices

        # modify the vertex locations
        verts[:,1:] *= mag
        verts[:,2] += xmin
        verts[:,1] += ymin
        verts[:,0] += smin
        verts[:,0] *= section_thickness

        # get the color
        color = self.color + (alpha,)

        # create the gl mesh object
        item = gl.GLMeshItem(
                vertexes=verts,
                faces=faces,
                color=color,
                shader="edgeDarken",
                glOptions="translucent",
                smooth=True,
        )

        return item


class Spheres(Object3D):

    def __init__(self, name):
        """Create a 3D Spheres object."""
        super().__init__(name)
        self.colors = []
        self.centroids = []
        self.radii = []
    
    def addTrace(self, trace : Trace, snum : int, tform : Transform = None):
        """Add a trace to the spheres data."""
        self.colors.append(tuple([c/255 for c in trace.color]))

        x, y = centroid(trace.points)
        if tform:
            x, y = tform.map(x, y)
        self.centroids.append((x, y, snum))
        self.addToExtremes(x, y, snum)

        self.radii.append(trace.getRadius(tform))
    
    def generate3D(self, section_thickness : float, alpha=1):
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
            x, y, s = point
            z = s * section_thickness
            item.translate(z, y, x)
            items.append(item)
        
        return items
