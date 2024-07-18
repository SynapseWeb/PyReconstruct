import numpy as np

from skimage.draw import polygon
import trimesh

from PyReconstruct.modules.calc import centroid
from PyReconstruct.modules.datatypes import Trace, Transform, Series


def exportMesh(tm, output_file, export_type):
    """Export trimesh obj to a file."""
    with open(output_file, "w") as fp:
            
        if export_type == "obj":
            
            with open(output_file, "w") as fp:
                fp.write(trimesh.exchange.obj.export_obj(tm))
                
        elif export_type == "off":
            
            with open(output_file, "w") as fp:
                fp.write(trimesh.exchange.off.export_off(tm))
                
        elif export_type == "ply":
            
            with open(output_file, "wb") as fp:
                fp.write(trimesh.exchange.ply.export_ply(tm))
                
        elif export_type == "stl":
            
            with open(output_file, "wb") as fp:
                fp.write(trimesh.exchange.stl.export_stl(tm))
                
        elif export_type == "dae":
            
            with open(output_file, "wb") as fp:
                fp.write(trimesh.exchange.dae.export_collada(tm))
                    

class Object3D():

    def __init__(self, name, series : Series, color=None, alpha=None, tform=None):
        self.name = name
        self.series = series
        self.color = color
        self.alpha = alpha
        self.tform = tform
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

    def __init__(self, *args):
        """Create a 3D Surface object."""
        super().__init__(*args)
        self.default_color = None
        self.traces = {}
    
    def addTrace(self, trace : Trace, snum : int, tform : Transform = None):
        """Add a trace to the surface data."""
        if self.default_color is None:
            self.default_color = trace.color
        
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

    def generateTrimesh(self):
        """Generate a trimesh object from traces."""
        # calculate the xy resolution for the volume
        vres_min = min(self.series.avg_mag, self.series.avg_thickness)
        vres_max = max(self.series.avg_mag, self.series.avg_thickness)
        vres_percent = self.series.getOption("3D_xy_res")
        vres = vres_min + (1 - vres_percent / 100) * (vres_max - vres_min)
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
        tm.metadata["color"] = self.color if self.color else self.default_color
        tm.metadata["alpha"] = self.series.getAttr(self.name, "3D_opacity")

        smoothing = self.series.getOption("3D_smoothing")
        iterations = self.series.getOption("smoothing_iterations")

        # smooth trimesh
        if smoothing == "humphrey":
            trimesh.smoothing.filter_humphrey(tm, iterations=iterations)
        elif smoothing == "laplacian":
            trimesh.smoothing.filter_laplacian(tm, iterations=iterations)
        elif smoothing == "mut_dif_laplacian":
            trimesh.smoothing.filter_mut_dif_laplacian(tm, iterations=iterations)
        elif smoothing == "taubin":
            trimesh.smoothing.filter_taubin(tm, iterations=iterations)

        # provide real vertex locations
        # (i.e., normalize to real world dimensions)
        tm.vertices[:,:2] *= vres
        tm.vertices[:,0] += xmin
        tm.vertices[:,1] += ymin
        tm.vertices[:,2] += smin
        tm.vertices[:,2] *= self.series.avg_thickness

        return tm

    def exportTrimesh(self, output_file, export_type):
        """Export trimesh object to file."""

        tm = self.generateTrimesh()
        exportMesh(tm, output_file, export_type)

    def generate3D(self):
        """Generate the openGL mesh for a surface object."""

        tm = self.generateTrimesh()

        mesh_data = {
            "name": self.name,
            "type": "object",
            "color": self.color if self.color else self.default_color,
            "alpha": self.alpha if self.alpha else self.series.getAttr(self.name, "3D_opacity"),
            "vertices": tm.vertices,
            "faces": tm.faces,
            "tform": self.tform
        }

        return mesh_data


class Spheres(Object3D):

    def __init__(self, *args):
        """Create a 3D Spheres object."""
        super().__init__(*args)
        self.colors = []
        self.centroids = []
        self.radii = []
    
    def addTrace(self, trace : Trace, snum : int, tform : Transform = None):
        """Add a trace to the spheres data."""
        self.colors.append(trace.color)

        x, y = centroid(trace.points)
        if tform:
            x, y = tform.map(x, y)
        self.centroids.append((x, y, snum))
        self.addToExtremes(x, y, snum)

        self.radii.append(trace.getRadius(tform))

    def generateTrimesh(self):
        """Generate trimesh object of spheres."""

        verts = []
        faces = []

        all_spheres = []
        
        for point, radius in zip(
            self.centroids,
            self.radii
        ):
            x, y, s = point
            z = s * self.series.avg_thickness
            sphere = trimesh.primitives.Sphere(radius=radius, center=(x,y,z), subdivisions=1)
            all_spheres.append(sphere)
            
            faces += (sphere.faces + len(verts)).tolist()
            verts += sphere.vertices.tolist()
        
        return trimesh.util.concatenate(all_spheres)

    def exportTrimesh(self, output_file, export_type):
        """Export trimesh sphere(s) to file."""

        tm = self.generateTrimesh()
        exportMesh(tm, output_file, export_type)
            
    def generate3D(self):
        """Generate the openGL meshes for sphere objects."""

        tm = self.generateTrimesh()
        
        mesh_data = {
            "name": self.name,
            "type": "object",
            "color": self.color if self.color else self.colors[0],
            "alpha": self.alpha if self.alpha else self.series.getAttr(self.name, "3D_opacity"),
            "vertices": np.array(tm.vertices),
            "faces": np.array(tm.faces),
            "tform": self.tform
        }
        
        return mesh_data

class Contours(Object3D):

    def __init__(self, *args):
        """Create a 3D Surface object."""
        super().__init__(*args)
        self.default_color = None
        self.traces = {}
    
    def addTrace(self, trace : Trace, snum : int, tform : Transform = None):
        """Add a trace to the surface data."""
        if self.default_color is None:
            self.default_color = trace.color
        
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
    
    def generate3D(self):
        """Generate openGL meshes for trace slabs."""
        
        verts = []
        faces = []
        
        for snum in self.traces:
            # get the z values
            t = self.series.avg_thickness
            z1 = snum * t
            z2 = z1 + t/2
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
            "type": "object",
            "color": self.color if self.color else self.default_color,
            "alpha": self.alpha if self.alpha else self.series.getAttr(self.name, "3D_opacity"),
            "vertices": np.array(verts),
            "faces": np.array(faces),
            "tform": self.tform
        }

        return mesh_data


class Ztrace3D(Object3D):
    
    def generate3D(self):
        """Generate the 3D object for the ztrace."""
        # ASSUME UNIFORM SECTION THICKNESS
        thickness = self.series.avg_thickness

        ztrace = self.series.ztraces[self.name]
        pts = []
        for pt in ztrace.points:
            # get coords
            x, y, s = pt
            self.addToExtremes(x, y, s)

            # get appropriate tform
            alignment = self.series.getAttr(self.name, "alignment", ztrace=True)
            if not alignment: alignment = self.series.alignment
            tform = self.series.data["sections"][s]["tforms"][alignment]

            # get real field coord point
            x, y = tform.map(x, y)
            z = s * thickness
            pts.append((x, y, z))
        
        d = ztrace.getDistance(self.series)
        color = ztrace.color

        verts, faces = createTube(pts, d/1000)

        mesh_data = {
            "name": self.name,
            "type": "ztrace",
            "color": self.color if self.color else color,
            "alpha": self.alpha if self.alpha else 1,
            "vertices": verts,
            "faces": faces,
            "tform": self.tform
        }

        return mesh_data


def getCircleVertices(radius, segments):
    """
    Generate vertices for a circle in the XY plane.
    
    :param radius: Radius of the circle
    :param segments: Number of segments (vertices) to generate around the circle
    :return: Numpy array of shape (segments, 3) containing the circle vertices
    """
    angles = np.linspace(0, 2 * np.pi, segments, endpoint=False)
    x = radius * np.cos(angles)
    y = radius * np.sin(angles)
    z = np.zeros(segments)
    return np.vstack((x, y, z)).T

def createTube(path_points, radius=0.1, segments=6):
    """Create a tube mesh.
    
        Params:
            path_points (list): the list of 3D points
            radius (float): the radius of the circle for the tube
            segments (int): the number of segments in the circle
    """
    # Generate the circular profile vertices
    circle_vertices = getCircleVertices(radius, segments)

    # Initialize lists to store vertices and faces
    vertices = []
    faces = []

    num_points = len(path_points)
    num_circle_vertices = len(circle_vertices)

    for i, point in enumerate(path_points):
        # Translate the circle profile to the current path point
        translated_vertices = circle_vertices + point
        vertices.extend(translated_vertices)

        if i > 0:
            # Connect the current profile with the previous profile
            for j in range(num_circle_vertices):
                next_j = (j + 1) % num_circle_vertices
                current_base = (i * num_circle_vertices) + j
                current_next = (i * num_circle_vertices) + next_j
                previous_base = ((i - 1) * num_circle_vertices) + j
                previous_next = ((i - 1) * num_circle_vertices) + next_j

                # Create two faces (a quad) between the profiles
                faces.append([previous_base, previous_next, current_next])
                faces.append([previous_base, current_next, current_base])

    # Convert lists to numpy arrays
    vertices = np.array(vertices)
    faces = np.array(faces)

    return vertices, faces

