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
            self.traces[snum] = {}
            self.traces[snum]["pos"] = []
            self.traces[snum]["neg"] = []
        
        pts = []
        for pt in trace.points:
            if tform:
                x, y = tform.map(*pt)
            else:
                x, y = pt
            self.addToExtremes(x, y, snum)
            pts.append((x, y))
        
        if trace.negative:
            self.traces[snum]["neg"].append(pts)
        else:
            self.traces[snum]["pos"].append(pts)
    
    def generate3D(self, section_mag, section_thickness, alpha=1, smoothing="none"):
        """Generate the numpy array volumes.
        """
        # set mag to four times average sections mag
        mag = section_mag * 8

        # calculate the dimensions of the volume
        xmin, xmax, ymin, ymax, smin, smax = tuple(self.extremes)
        vshape = (
            round((xmax-xmin)/mag)+1,
            round((ymax-ymin)/mag)+1,
            smax-smin+1
        )
    
        # create the numpy volume
        volume = np.zeros(vshape, dtype=bool)

        # add the traces to the volume
        for snum, trace_lists in self.traces.items():
            for trace in trace_lists["pos"]:
                x_values = []
                y_values = []
                for x, y in trace:
                    x_values.append(round((x-xmin) / mag))
                    y_values.append(round((y-ymin) / mag))
                x_pos, y_pos = polygon(
                    np.array(x_values),
                    np.array(y_values)
                )
                volume[x_pos, y_pos, snum - smin] = True
            # subtract out the negative traces
            for trace in trace_lists["neg"]:
                x_values = []
                y_values = []
                for x, y in trace:
                    x_values.append(round((x-xmin) / mag))
                    y_values.append(round((y-ymin) / mag))
                x_pos, y_pos = polygon(
                    np.array(x_values),
                    np.array(y_values)
                )
                volume[x_pos, y_pos, snum - smin] = False

        # generate and smooth the trimesh
        tm = trimesh.voxel.ops.matrix_to_marching_cubes(volume)
        if smoothing == "humphrey":
            trimesh.smoothing.filter_humphrey(tm)
        elif smoothing == "laplacian":
            trimesh.smoothing.filter_laplacian(tm)

        faces = tm.faces
        verts = tm.vertices

        # modify the vertex locations
        verts[:,:2] *= mag
        verts[:,0] += xmin
        verts[:,1] += ymin
        verts[:,2] += smin
        verts[:,2] *= section_thickness

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

        return tm.volume, item


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
            volume = 4/3 * np.pi * radius**3
            item.translate(z, y, x)
            items.append((volume, item))
        
        return items
