import numpy as np

from PySide6.QtGui import QKeySequence, QShortcut

import pyqtgraph.opengl as gl

from modules.backend.generate_3D import ObjectVolume

from modules.pyrecon.series import Series

class Object3DViewer(gl.GLViewWidget):

    def __init__(self, series : Series, obj_names : list, opacity : int, sc_size : float, mainwindow):
        """Create the 3D View.
            
            Params:
                series (Series): the series object
                obj_names (list): the name of objects to plot
                opacity (int): the opacity of the 3D objects
                sc_size (float): the size of the scale cube
                mainwindow: the main window
        """
        super().__init__()

        self.opacity = opacity
        self.sc_size = sc_size

        self.setWindowTitle("3D Object Viewer")
        self.setGeometry(
            mainwindow.x()+20,
            mainwindow.y()+20,
            mainwindow.width()-40,
            mainwindow.height()-40
        )

        # create scale sube shortcut
        QShortcut(QKeySequence("s"), self).activated.connect(self.createScaleCube)
        self.sc_item = None

        # generate the volume
        obj_vol = ObjectVolume(series, obj_names)
        if obj_vol.canceled:
            return
        self.vol_item, shape, offset = obj_vol.generateVolume(alpha=self.opacity)

        # adjust the volume item to fit the view
        z, y, x = shape
        self.vol_item.translate(-z/2, -y/2, -x/2)
        self.vol_item.rotate(-90, 0, 1, 0)

        self.opts['distance'] = max(x, y, z)

        self.addItem(self.vol_item)

        self.setBackgroundColor((255, 255, 255))
        self.show()

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
        verts_box = np.array([
        [ 0, 0, 0],
        [ 1, 0, 0],
        [ 1, 1, 0],
        [ 0, 1, 0],
        [ 0, 0, 1],
        [ 1, 0, 1],
        [ 1, 1, 1],
        [ 0, 1, 1]],
        dtype=float) * self.sc_size

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
            c = i/10+0.2
            for _ in range(2):
                colors_box.append([c,c,c,0.5])
        colors_box = np.array(colors_box)

        self.sc_item = gl.GLMeshItem(
            vertexes=verts_box,
            faces=faces_box,
            faceColors=colors_box,
            smooth=False
        )

        self.removeItem(self.vol_item)
        self.addItem(self.sc_item)
        self.addItem(self.vol_item) 
    
    # def createScaleCube(self, size=1, outline_color=[0,0,0,255], face_color=[192,192,192,255]):
    #     if self.sc_item:
    #         self.removeItem(self.sc_item)
    #     s = 64
    #     sc_volume = np.zeros(shape=(s, s, s, 4))

    #     # color the faces
    #     for x in (0, -1):
    #         sc_volume[x,:,:] = face_color
    #         for y in (0, -1):
    #             sc_volume[:,y,:] = face_color
    #             for z in (0, -1):
    #                 sc_volume[:,:,z] = face_color
        
    #     # color the outlines
    #     for x in (0, -1):
    #         for y in (0, -1):
    #             for z in (0, -1):
    #                 sc_volume[:,y,z] = outline_color
    #                 sc_volume[x,:,z] = outline_color
    #                 sc_volume[x,y,:] = outline_color

    #     # generate the volume
    #     self.sc_item = gl.GLVolumeItem(sc_volume)
    #     self.sc_item.scale(size/s, size/s, size/s)
    #     # add to scene
    #     self.removeItem(self.vol_item)
    #     self.addItem(self.sc_item)
    #     self.addItem(self.vol_item)

        # create the shortcuts
        self.createScaleCubeShortcuts()

    
    def moveScaleCube(self, dx, dy, dz):
        self.sc_item.translate(dx, dy, dz)
