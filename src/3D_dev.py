import sys
import cv2
import numpy as np

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QTransform

import pyqtgraph.opengl as gl

from modules.pyrecon.series import Series

def tformScalePoints(points : list, t : list, mag : float) -> list[tuple[int]]:
    """Transform and scale a set of points."""
    point_tform = QTransform(t[0], t[3], t[1], t[4], t[2], t[5])
    new_points = []
    for p in points:
        x, y = point_tform.map(*p)
        new_points.append((
            round(x / mag),
            round(y / mag)
        ))
    return new_points

def loadSeriesObjects(series : Series, obj_names : list[str], mag : float):
    # create objects dictionary
    objs = {}
    for obj_name in obj_names:
        objs[obj_name] = {}
    z_pos_list = []
    
    # iterate through all the sections and gather traces
    for snum in series.sections:
        section = series.loadSection(snum)
        for obj_name in obj_names:
            # check if object exists in section
            if obj_name not in section.traces:
                continue
            # transform and scale points and add them to list
            z_pos = round(snum * section.thickness / mag)
            z_pos_list.append(z_pos)
            objs[obj_name][z_pos] = []
            for trace in section.traces[obj_name]:
                modified_points = tformScalePoints(
                    trace.points,
                    section.tforms[series.alignment],
                    mag
                )
                objs[obj_name][z_pos].append({
                    "points" : modified_points,
                    "color" : trace.color
                })
    
    return objs, z_pos_list

def getObjectsBounds(objects : dict):
    xmin = None
    ymin = None
    xmax = None
    ymax = None
    zmin = None
    zmax = None
    for obj in objects:
        for z in objects[obj]:
            if zmin is None or z < zmin: zmin = z
            if zmax is None or z > zmax: zmax = z
            for trace in objects[obj][z]:
                for x, y in trace["points"]:
                    if xmin is None or x < xmin: xmin = x
                    if xmax is None or x > xmax: xmax = x
                    if ymin is None or y < ymin: ymin = y
                    if ymax is None or y > ymax: ymax = y
    
    return xmin, ymin, zmin, xmax, ymax, zmax

def fillInSlices(volume : np.ndarray, z_pos_list : list):
    for z in range(volume.shape[0]):
        if z in z_pos_list:
            slice = volume[z]
        else:
            volume[z] = slice

def generateVolume(series : Series, obj_names : list[str], mag : float, alpha=100):
    objs, z_pos_list = loadSeriesObjects(series, obj_names, mag)
    xmin, ymin, zmin, xmax, ymax, zmax = getObjectsBounds(objs)
    volume = np.zeros(
        (zmax-zmin+1, ymax-ymin+1, xmax-xmin+1, 4),
        dtype=np.ubyte
    )
    for obj in objs:
        for z in objs[obj]:
            for trace in objs[obj][z]:
                pts = np.array(trace["points"])
                pts[:,0] -= xmin
                pts[:,1] -= ymin
                cv2.fillPoly(
                    img=volume[z-zmin],
                    pts=[pts],
                    color=trace["color"] + [alpha]
                )
    
    fillInSlices(volume, [z - zmin for z in z_pos_list])

    return volume

class TraceViewer():
    def __init__(self):
        self.w = gl.GLViewWidget()
        self.w.setWindowTitle('pyqtgraph example: GLLinePlotItem')
        self.w.setGeometry(20, 20, 1000, 1000)
        self.w.show()
    
    def plotVolume(self, volume : np.ndarray):
        volume[:,0,0] = [0, 0, 255, 255]
        volume[0,:,0] = [0, 255, 0, 255]
        volume[0,0,:] = [255, 0, 0, 255]
        v = gl.GLVolumeItem(volume)
        z, y, x, _ = volume.shape
        print("Volume:", z*y*x)
        v.translate(-z/2, -y/2, -x/2)
        v.rotate(-90, 0, 1, 0)
        self.w.opts['distance'] = max(x, y, z)
        self.w.addItem(v)


# Start Qt event loop unless running in interactive mode.
if __name__ == '__main__':
    series = Series(r"C:\Users\jfalco\Documents\Series\DSNYJ_JSON_D001\DSNYJ.ser")
    obj_names = ["d001"]
    for i in range(100):
        obj_names.append(f"d001c{i:03}")

    volume = generateVolume(series, obj_names, 0.02)
    

    app = QApplication(sys.argv)
    t = TraceViewer()
    t.plotVolume(volume)
    app.exec()