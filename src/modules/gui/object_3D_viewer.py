import numpy as np

from PySide6.QtGui import QKeySequence, QShortcut

import pyqtgraph.opengl as gl
from pyqtgraph.Vector import Vector

from modules.backend.generate_volumes import generateVolumes

from modules.pyrecon.series import Series

class Object3DViewer(gl.GLViewWidget):

    def __init__(self, series : Series, obj_names : list, opacity : int, sc_size : float, mainwindow):
        """Create the 3D View.
            
            Params:
                series (Series): the series object
                obj_names (list): the name of objects to plot
                opacity (int): the opacity of the 3D objects
                sc_size (float): the size of the scale cube
                mainwindow (MainWindow): the main window
        """
        super().__init__()

        # custom shader: colors get darker near the edges
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
                    float s = pow(normal.x*normal.x + normal.y*normal.y, 2) / 3;
                    color.x = color.x - s * color.x;
                    color.y = color.y - s * color.y;
                    color.z = color.z - s * color.z;
                    gl_FragColor = color;
                }
            """)
        ]))

        self.series = series
        self.opacity = opacity
        self.sc_size = sc_size
        self.obj_set = set(obj_names)

        self.setWindowTitle("3D Object Viewer")
        self.setGeometry(
            mainwindow.x()+20,
            mainwindow.y()+20,
            mainwindow.width()-40,
            mainwindow.height()-40
        )

        # create scale sube shortcut
        QShortcut(QKeySequence("s"), self).activated.connect(self.toggleScaleCube)

        # get the items
        items, extremes = generateVolumes(
            self.series,
            obj_names,
            self.opacity
        )
        # add the items to the scene
        for item in items:
            self.addItem(item)
        
        # center the camera view        
        xavg = (extremes[0] + extremes[1]) / 2
        yavg = (extremes[2] + extremes[3]) / 2
        zavg = (extremes[4] + extremes[5]) / 2
        self.center = Vector(xavg, yavg, zavg)
        self.setCameraPosition(
            pos=self.center,
            distance=max(extremes)
        )

        self.setBackgroundColor((255, 255, 255))

        self.sc_in_scene = False
        self.createScaleCube()

        self.show()
    
    def addObjects(self, obj_names):
        """Add objects to the existing scene.
        
            Params:
                obj_names (list): the names of the objects to add
        """
        # get new names and add names to existing set
        obj_names = list(set(obj_names).difference(self.obj_set))
        if not obj_names:
            return
        self.obj_set = self.obj_set.union(obj_names)

        items, extremes = generateVolumes(
            self.series,
            obj_names,
            self.opacity
        )

        for item in items:
            self.addItem(item)

    def createScaleCubeShortcuts(self):
        """Create the shortcuts for the 3D scene."""
        shortcuts = [
            # ("s", self.scaleCubeSize),
            ("Left", lambda : self.moveScaleCube(-0.1, 0, 0)),
            ("Right", lambda : self.moveScaleCube(0.1, 0, 0)),
            ("Up", lambda : self.moveScaleCube(0, 0.1, 0)),
            ("Down", lambda : self.moveScaleCube(0, -0.1, 0)),
            ("Ctrl+Up", lambda : self.moveScaleCube(0, 0, 0.1)),
            ("Ctrl+Down", lambda : self.moveScaleCube(0, 0, -0.1))
        ]
        for kbd, act in shortcuts:
            QShortcut(QKeySequence(kbd), self).activated.connect(act)
    
    def createScaleCube(self):
        """Create the scale cube to display in the 3D environment."""
        verts_box = np.array(
            [
                [ 0, 0, 0],
                [ 1, 0, 0],
                [ 1, 1, 0],
                [ 0, 1, 0],
                [ 0, 0, 1],
                [ 1, 0, 1],
                [ 1, 1, 1],
                [ 0, 1, 1]
            ],
            dtype=float
        ) * self.sc_size

        faces_box = np.array([
            [0, 1, 2],
            [0, 2, 3],
            [0, 1, 4],
            [1, 5, 4],
            [1, 2, 5],
            [2, 5, 6],
            [2, 3, 6],
            [3, 6, 7],
            [0, 3, 7],
            [0, 4, 7],
            [4, 5, 7],
            [5, 6, 7],
        ])

        colors_box = []
        for i in range(1, 7):
            c = i/10+0.1
            for _ in range(2):
                colors_box.append([c,c,c,1])
        colors_box = np.array(colors_box)

        self.sc_item = gl.GLMeshItem(
            vertexes=verts_box,
            faces=faces_box,
            faceColors=colors_box,
            smooth=False
        )

        self.sc_item.translate(
            self.center.x(),
            self.center.y(),
            self.center.z()
        )

        # create the shortcuts
        self.createScaleCubeShortcuts()
    
    def toggleScaleCube(self):
        """Toggle the scale cube on the 3D scene."""

        # sphere = gl.MeshData.sphere(rows=10, cols=10, radius=1)
        # m1 = gl.GLMeshItem(
        #     meshdata=sphere,
        #     smooth=True,
        #     color=(1, 0, 0, 1),
        #     shader="edgeDarken",
        #     glOptions="opaque",
        # )
        # m1.translate(
        #     self.center.x(),
        #     self.center.y(),
        #     self.center.z()
        # )
        # self.addItem(m1)

        if self.sc_in_scene:
            self.removeItem(self.sc_item)
        else:
            self.addItem(self.sc_item)
        self.sc_in_scene = not self.sc_in_scene

    def moveScaleCube(self, dx, dy, dz):
        """Translate the scale cube."""
        self.sc_item.translate(dx, dy, dz)
