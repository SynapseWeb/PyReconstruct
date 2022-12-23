import numpy as np

from PySide6.QtWidgets import QInputDialog, QMenu, QColorDialog
from PySide6.QtGui import QKeySequence, QShortcut

import pyqtgraph.opengl as gl
from pyqtgraph.Vector import Vector

from modules.backend.generate_volumes import generateVolumes

from modules.pyrecon.series import Series

from modules.gui.gui_functions import populateMenu

class Object3DViewer(gl.GLViewWidget):

    def __init__(self, series : Series, obj_names : list, mainwindow):
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
                    float s = pow(normal.x*normal.x + normal.y*normal.y, 3.0) / 2.0;
                    color.x = color.x - s * color.x;
                    color.y = color.y - s * color.y;
                    color.z = color.z - s * color.z;
                    gl_FragColor = color;
                }
            """)
        ]))

        self.series = series
        self.sc_side_len = 1
        self.obj_set = set(obj_names)
        self.closed = False

        self.setWindowTitle("3D Object Viewer")
        self.setGeometry(
            mainwindow.x()+60,
            mainwindow.y()+60,
            mainwindow.width()-120,
            mainwindow.height()-120
        )

        # get the items
        items, extremes = generateVolumes(
            self.series,
            obj_names,
        )
        # add the items to the scene
        for item in items:
            self.addItem(item)
        
        # center the camera view        
        xavg = (extremes[0] + extremes[1]) / 2
        yavg = (extremes[2] + extremes[3]) / 2
        zavg = (extremes[4] + extremes[5]) / 2

        diffs = [extremes[i] - extremes[i-1] for i in (1, 3, 5)]
        self.center = Vector(xavg, yavg, zavg)
        self.setCameraPosition(
            pos=self.center,
            distance=max(diffs)*2
        )

        self.setBackgroundColor((255, 255, 255))

        self.sc_in_scene = False
        self.createScaleCube()

        self.createContextMenu()

        self.show()
    
    def createContextMenu(self):
        """Create the context menu for the 3D scene."""
        context_menu_list = [
            ("togglesc_act", "Toggle scale cube", "S", self.toggleScaleCube),
            ("editscsize_act", "Edit scale cube size...", "", self.editSCSize),
            ("background_act", "Set background color...", "", self.editBackgroundColor)
        ]
        self.context_menu = QMenu(self)
        populateMenu(self, self.context_menu, context_menu_list)
    
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
        )

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
            c = i/10+0.05
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
    
    def contextMenuEvent(self, event):
        """Execute the context menu when user right clicks."""
        self.context_menu.exec(event.globalPos())
    
    def toggleScaleCube(self):
        """Toggle the scale cube on the 3D scene."""
        if self.sc_in_scene:
            self.removeItem(self.sc_item)
        else:
            self.addItem(self.sc_item)
        self.sc_in_scene = not self.sc_in_scene
    
    def editSCSize(self):
        """Modify the size of the scale cube."""
        new_side_len, confirmed = QInputDialog.getText(
            self,
            "Scale Cube Size",
            "Enter the scale cube side length (in µm):"
        )
        if not confirmed:
            return

        try:
            new_side_len = float(new_side_len)
        except ValueError:
            return
        
        scale = new_side_len / self.sc_side_len
        self.sc_item.scale(scale, scale, scale)
        self.sc_side_len = new_side_len
    
    def editBackgroundColor(self):
        """Edit the background color of the 3D scene."""
        color = QColorDialog.getColor()
        if color.isValid():
            self.setBackgroundColor((color.red(), color.green(), color.blue()))

    def moveScaleCube(self, dx, dy, dz):
        """Translate the scale cube."""
        self.sc_item.translate(dx, dy, dz)
    
    def closeEvent(self, event):
        """Executed when closed."""
        self.closed = True
        super().closeEvent(event)

