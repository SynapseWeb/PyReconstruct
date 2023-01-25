import sys
from PySide6.QtWidgets import QApplication

import numpy as np

from skimage.draw import polygon
from skimage import measure

from pyvista import PolyData

import trimesh

from time import time

import pyqtgraph.opengl as gl

from modules.pyrecon.series import Series

class ObjectVolume():

    def __init__(self, series : Series, obj_names : list[str]):
        """Load the objects in a series.
        
            Params:
                series (Series): the series object
                obj_names (list): the list of objects to gather data for
        """
        # create objects dictionary
        self.obj_data = {}
        for name in obj_names:
            self.obj_data[name] = {}
            self.obj_data[name]["color"] = None
            self.obj_data[name]["points"] = {}

        # assume uniform section thickness
        self.section_thickness = None

        # store average mag
        self.avg_mag = 0
        
        # iterate through all the sections and gather traces
        for snum in series.sections:
            section = series.loadSection(snum)

            # store section thickness
            if self.section_thickness is None:
                self.section_thickness = section.thickness
            
            # get mag
            self.avg_mag += section.mag
            
            # load the object points
            for obj_name in obj_names:

                # check if object exists in section
                if obj_name not in section.contours:
                    continue
    
                # transform points and add them to list
                self.obj_data[obj_name]["points"][snum] = []
                tform = section.tforms[series.alignment]
                for trace in section.contours[obj_name]:
                    modified_points = tform.map(trace.points)
                    self.obj_data[obj_name]["points"][snum].append(
                        modified_points
                    )

                    # check for color
                    if self.obj_data[obj_name]["color"] is None:
                        self.obj_data[obj_name]["color"] = trace.color
        
        self.avg_mag /= len(series.sections)
        
        # generate volume bounds
        self.getVolumeBounds()

    def getVolumeBounds(self):
        """Get the x, y, and z min and max values for the volume from self.objs.
        
            Returns:
                xmin, ymin, zmin, xmax, ymax, zmax
        """
        for obj_name in self.obj_data:
            xmin = None
            ymin = None
            xmax = None
            ymax = None
            zmin = None
            zmax = None

            z_values = list(self.obj_data[obj_name]["points"].keys())
            zmin = min(z_values)
            zmax = max(z_values)

            for z in z_values:
                for trace in self.obj_data[obj_name]["points"][z]:
                    for x, y in trace:
                        if xmin is None or x < xmin: xmin = x
                        if xmax is None or x > xmax: xmax = x
                        if ymin is None or y < ymin: ymin = y
                        if ymax is None or y > ymax: ymax = y
            
            self.obj_data[obj_name]["bounds"] = xmin, ymin, zmin, xmax, ymax, zmax
    
    def addShader(self):
        """Add the edgeDarken shader to the opengl shaders if not already added."""
        names = [s.name for s in gl.shaders.Shaders]
        if "edgeDarken" not in names:
            gl.shaders.Shaders.append(gl.shaders.ShaderProgram('edgeDarken', [
                gl.shaders.VertexShader("""
                    varying vec3 normal;
                    void main() {
                        // compute here for use in fragment shader
                        normal = normalize(gl_NormalMatrix * gl_Normal);
                        gl_FrontColor = gl_Color;
                        gl_BackColor = gl_Color;
                        gl_Position = ftransform();
                    }
                """),
                gl.shaders.FragmentShader("""
                    varying vec3 normal;
                    void main() {
                        vec4 color = gl_Color;
                        float s = pow(normal.x*normal.x + normal.y*normal.y, 3.0) / 2.0;
                        color.x = color.x - s * color.x;
                        color.y = color.y - s * color.y;
                        color.z = color.z - s * color.z;
                        gl_FragColor = color;
                    }
                """)
            ]))

    def generateVolumes(self, alpha=1):
        """Generate the numpy array volumes.
        """
        volume_dict = {}

        # set mag to four times average sections mag
        mag = self.avg_mag * 8

        # iterate through the objects
        for obj_name, obj_dict in self.obj_data.items():
            # calculate the dimensions of the volume
            xmin, ymin, zmin, xmax, ymax, zmax = obj_dict["bounds"]
            vshape = (
                zmax-zmin+1,
                round((ymax-ymin)/mag)+1,
                round((xmax-xmin)/mag)+1
            )
        
            # create the numpy volume
            volume = np.zeros(vshape, dtype=bool)

            # add the traces to the volume
            for z, trace_list in obj_dict["points"].items():
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
                    volume[z - zmin, y_pos, x_pos] = True
            
            print("voxels generated")

            tm = trimesh.voxel.ops.matrix_to_marching_cubes(volume)

            print("initial trimesh generated")

            trimesh.smoothing.filter_laplacian(tm)

            print("smoothed")

            tm : trimesh.Trimesh

            faces = tm.faces
            verts = tm.vertices

            print("trimesh generated")

            # get the color
            color = [c/255 for c in obj_dict["color"]] + [alpha]

            # # modify the verts to fit actual coordinates
            # verts[:,:2] *= mag
            # verts[:,0] += xmin
            # verts[:,1] += ymin
            # verts[:,2] += zmin
            # verts[:,2] /= self.section_thickness

            # create the gl mesh object
            self.addShader()
            item = gl.GLMeshItem(
                    vertexes=verts,
                    faces=faces,
                    color=color,
                    shader="edgeDarken",
                    glOptions="translucent",
                    smooth=True,
            )
            item.scale(self.section_thickness / mag, 1, 1)

            volume_dict[obj_name] = item
        
        return volume_dict

class Object3DViewer(gl.GLViewWidget):

    def __init__(self, mesh_dict : dict):
        super().__init__()

        # add the items to the scene
        for item in mesh_dict.values():
            self.addItem(item)
        
        self.setBackgroundColor((255, 255, 255))

        self.show()

t1 = time()
series = Series(
    r"C:\Users\jfalco\Documents\Series\DSNYJ_JSER\.DSNYJ\DSNYJ.ser"
)
obj_names = ["d005"]
volume = ObjectVolume(series, obj_names)
mesh_dict = volume.generateVolumes()
print(time() - t1)

app = QApplication(sys.argv)
v = Object3DViewer(mesh_dict)
app.exec()