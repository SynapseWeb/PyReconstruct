import numpy as np
from numpy._typing import _Float16Codes

from skimage.draw import polygon
import trimesh
from vtkmodules.vtkFiltersGeneral import vtkCountVertices

from PyReconstruct.modules.calc import centroid
from PyReconstruct.modules.datatypes import Trace, Transform

def exportMesh(tm, output_file, export_type):
    """Export a trimesh to a file."""
    with open(output_file, "w") as fp:
        
        match export_type:
            
            case "obj":
                
                with open(output_file, "w") as fp:
                    fp.write(trimesh.exchange.obj.export_obj(tm))
                    
            case "off":
                
                with open(output_file, "w") as fp:
                    fp.write(trimesh.exchange.off.export_off(tm))
                    
            case "ply":
                
                with open(output_file, "wb") as fp:
                    fp.write(trimesh.exchange.ply.export_ply(tm))
                    
            case "stl":
                
                with open(output_file, "wb") as fp:
                    fp.write(trimesh.exchange.stl.export_stl(tm))
                    
            case "dae":
                
                with open(output_file, "wb") as fp:
                    fp.write(trimesh.exchange.dae.export_collada(tm))
                    
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

    def generateTrimesh(self, vres, section_thickness, alpha=1, smoothing="none"):
        """Generate a trimesh object from traces."""
        # calculate the dimensions of bounding box for empty array
        xmin, xmax, ymin, ymax, smin, smax = tuple(self.extremes)
        vshape = (
            round((xmax-xmin)/vres)+1,
            round((ymax-ymin)/vres)+1,
            smax-smin+1
        )
    
        # create empty numpy volume
        volume = np.zeros(vshape, dtype=bool)

        # add the traces to the volume
        for snum, trace_lists in self.traces.items():
            for trace in trace_lists["pos"]:
                x_values = []
                y_values = []
                for x, y in trace:
                    x_values.append(round((x-xmin) / vres))
                    y_values.append(round((y-ymin) / vres))
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
                    x_values.append(round((x-xmin) / vres))
                    y_values.append(round((y-ymin) / vres))
                x_pos, y_pos = polygon(
                    np.array(x_values),
                    np.array(y_values)
                )
                volume[x_pos, y_pos, snum - smin] = False

        # generate trimesh
        tm = trimesh.voxel.ops.matrix_to_marching_cubes(volume)
        tm : trimesh.base.Trimesh

        # add metadata
        tm.metadata["name"] = self.name
        tm.metadata["color"] = self.color
        tm.metadata["alpha"] = alpha

        # smooth trimesh
        if smoothing == "humphrey":
            trimesh.smoothing.filter_humphrey(tm)
        elif smoothing == "laplacian":
            trimesh.smoothing.filter_laplacian(tm, iterations=5)  # limit drift

        # provide real vertex locations
        # (i.e., normalize to real world dimensions)
        tm.vertices[:,:2] *= vres
        tm.vertices[:,0] += xmin
        tm.vertices[:,1] += ymin
        tm.vertices[:,2] += smin
        tm.vertices[:,2] *= section_thickness

        return tm

    def exportTrimesh(self, output_file, export_type, vres, section_thickness, alpha=1, smoothing="none"):
        """Export trimesh object to file."""

        tm = self.generateTrimesh(vres, section_thickness, alpha, smoothing)
        exportMesh(tm, output_file, export_type)

    def generate3D(self, vres, section_thickness, alpha=1, smoothing="none"):
        """Generate the openGL mesh for a surface object."""

        tm = self.generateTrimesh(vres, section_thickness, alpha, smoothing)

        mesh_data = {
            "name": self.name,
            "color": self.color,
            "alpha": alpha,
            "vertices": tm.vertices,
            "faces": tm.faces
        }

        return mesh_data


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

    def generateTrimesh(self, section_thickness, alpha=1):
        """Generate trimesh object of spheres."""

        verts = []
        faces = []

        all_spheres = []
        
        for point, radius in zip(
            self.centroids,
            self.radii
        ):
            x, y, s = point
            z = s * section_thickness
            sphere = trimesh.primitives.Sphere(radius=radius, center=(x,y,z), subdivisions=1)
            all_spheres.append(sphere)
            
            faces += (sphere.faces + len(verts)).tolist()
            verts += sphere.vertices.tolist()
        
        return trimesh.util.concatenate(all_spheres)

    def exportTrimesh(self, output_file, export_type, section_thickness, alpha=1):
        """Export trimesh sphere(s) to file."""

        tm = self.generateTrimesh(section_thickness, alpha)
        exportMesh(tm, output_file, export_type)
            
    def generate3D(self, section_thickness : float, alpha=1):
        """Generate the openGL meshes for sphere objects."""

        tm = self.generateTrimesh(section_thickness, alpha)
        
        mesh_data = {
            "name": self.name,
            "color": self.colors[0],
            "alpha": alpha,
            "vertices": np.array(tm.vertices),
            "faces": np.array(tm.faces)
        }
        
        return mesh_data

class Contours(Object3D):

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
        
        if trace.closed:
            pts.append(pts[0])
        
        self.traces[snum].append(pts)
    
    def generate3D(self, section_thickness, alpha=1):
        """Generate openGL meshes for trace slabs."""
        
        verts = []
        faces = []
        
        for snum in self.traces:
            # get the z values
            z1 = snum * section_thickness
            z2 = z1 + section_thickness/2
            for trace in self.traces[snum]:
                for i in range(len(trace)-1):
                    # get the xy coords of the points
                    x1, y1 = trace[i]
                    x2, y2 = trace[i+1]
                    # gather the four points to create the slab section
                    verts.append([x1, y1, z1])
                    verts.append([x2, y2, z1])
                    verts.append([x2, y2, z2])
                    verts.append([x1, y1, z2])
                    # create the faces
                    l = len(verts)
                    faces.append([l-4, l-3, l-2])
                    faces.append([l-4, l-2, l-1])
        
        mesh_data = {
            "name": self.name,
            "color": self.color,
            "alpha": alpha,
            "vertices": np.array(verts),
            "faces": np.array(faces)
        }

        return mesh_data
