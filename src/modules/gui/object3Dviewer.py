import numpy as np

import pyqtgraph.opengl as gl

from modules.backend.generate_3D import ObjectVolume

from modules.pyrecon.series import Series

class Object3DViewer(gl.GLViewWidget):

    def __init__(self, series : Series, obj_names : list, mainwindow):
        """Create the 3D View.
            
            Params:
                series (Series): the series object
                obj_names (list): the name of objects to plot
                mainwindow: the main window
        """
        super().__init__()

        self.setWindowTitle("3D Object Viewer")
        self.setGeometry(
            mainwindow.x()+20,
            mainwindow.y()+20,
            mainwindow.width()-40,
            mainwindow.height()-40
        )

        # generate the volume
        obj_vol = ObjectVolume(series, obj_names)
        volume = obj_vol.generateVolume()
    
        # guide lines (xyz : rgb)
        volume[:,0,0] = [0, 0, 255, 255]
        volume[0,:,0] = [0, 255, 0, 255]
        volume[0,0,:] = [255, 0, 0, 255]

        # create the volume object in opengl
        v = gl.GLVolumeItem(volume)

        # move the object for better user interaction
        z, y, x, _ = volume.shape
        v.translate(-z/2, -y/2, -x/2)
        v.rotate(-90, 0, 1, 0)
        self.opts['distance'] = max(x, y, z)

        # add to scene and display
        self.addItem(v)
        self.show()