import numpy as np
from pyvista.core.pointset import PolyData, UnstructuredGrid
from modules.pyrecon.series import Series

import numpy as np

from PySide6.QtGui import QKeySequence, QShortcut

from PySide6.QtWidgets import QApplication
import sys
import pyqtgraph.opengl as gl

from modules.pyrecon.series import Series

def generateVolume():
    series = Series(r"C:\Users\jfalco\Documents\Series\DSNYJ_JSON\DSNYJ.ser")

    obj_name = "d001"

    points = []
    z = 0
    for snum in range(78, 278):
        section = series.loadSection(snum)
        tform = section.tforms[series.alignment]
        if obj_name in section.contours:
            for trace in section.contours[obj_name]:
                for pt in trace.points:
                    x, y = tform.map(*pt)
                    points.append((x, y, z))
        z += section.thickness

    ###############################################################################
    # Create a point cloud from a sphere and then reconstruct a surface from it.

    pdata = PolyData(np.array(points))
    surf = pdata.delaunay_3d(alpha=0.1)
    surf : UnstructuredGrid
    new_pdata = surf.extract_surface()
    print(type(new_pdata.points))
    for i, n in enumerate(new_pdata.faces):
        if i % 4 == 0:
            if n != 3:
                print("fuck")
    
    verts = new_pdata.points
    print(new_pdata.faces.shape)
    faces = new_pdata.faces.reshape((int(new_pdata.faces.shape[0]/4), 4))
    faces = faces[:, 1:]

    sc_item = gl.GLMeshItem(
            vertexes=verts,
            faces=faces,
            color=[255,255,0,1],
            shader="normalColor",
            glOptions="opaque",
            smooth=True
    )

    return sc_item

    

###############################################################################
# Plot the point cloud and the reconstructed sphere.

# pl = pv.Plotter(shape=(1, 2))
# pl.add_mesh(pdata)
# pl.add_title('Point Cloud of 3D Surface')
# pl.subplot(0, 1)
# pl.add_mesh(new_pdata, color=True, show_edges=False)
# pl.add_title('Reconstructed Surface')
# pl.show()

class Object3DViewer(gl.GLViewWidget):

    def __init__(self, sc_size : float = 1):
        """Create the 3D View.
            
            Params:
                series (Series): the series object
                obj_names (list): the name of objects to plot
                opacity (int): the opacity of the 3D objects
                sc_size (float): the size of the scale cube
                mainwindow (MainWindow): the main window
        """
        super().__init__()

        self.sc_size = sc_size

        # create scale sube shortcut
        QShortcut(QKeySequence("s"), self).activated.connect(self.toggleScaleCube)
        self.sc_item = None

        self.vol_item = generateVolume()

        self.addItem(self.vol_item)

        self.setBackgroundColor((255, 255, 255))

        self.sc_in_scene = False
        self.createScaleCube()

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
        """Create the scale cube to display in the 3D environment."""
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

        # create the shortcuts
        self.createScaleCubeShortcuts()
    
    def toggleScaleCube(self):
        """Toggle the scale cube on the 3D scene."""
        if self.sc_in_scene:
            self.removeItem(self.sc_item)
        else:
            self.removeItem(self.vol_item)
            self.addItem(self.sc_item)
            self.addItem(self.vol_item) 
        self.sc_in_scene = not self.sc_in_scene

    def moveScaleCube(self, dx, dy, dz):
        """Translate the scale cube."""
        self.sc_item.translate(dx, dy, dz)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = Object3DViewer()
    app.exec()

