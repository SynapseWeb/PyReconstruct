import sys
import cv2
import numpy as np

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QTransform

import pyqtgraph.opengl as gl

from modules.pyrecon.series import Series

class ObjectVolume():

    def __init__(self, series : Series, obj_names : list[str], mag : float = 0.025):
        """Load the objects in a series.
        
            Params:
                series (Series): the series object
                obj_names (list): the list of objects to gather data for
        """
        # create objects dictionary
        self.objs = {}
        for obj_name in obj_names:
            self.objs[obj_name] = {}
        # keep trck of z coordinates
        self.z_pos_list = []
        
        # iterate through all the sections and gather traces
        for snum in series.sections:
            section = series.loadSection(snum)
            for obj_name in obj_names:
                # check if object exists in section
                if obj_name not in section.traces:
                    continue
                # transform and scale points and add them to list
                z_pos = round(snum * section.thickness / mag)
                self.z_pos_list.append(z_pos)
                self.objs[obj_name][z_pos] = []
                for trace in section.traces[obj_name]:
                    modified_points = tformScalePoints(
                        trace.points,
                        section.tforms[series.alignment],
                        mag
                    )
                    self.objs[obj_name][z_pos].append({
                        "points" : modified_points,
                        "color" : trace.color
                    })

    def getVolumeBounds(self) -> tuple[int]:
        """Get the x, y, and z min and max values for the volume from self.objs.
        
            Returns:
                xmin, ymin, zmin, xmax, ymax, zmax
        """
        xmin = None
        ymin = None
        xmax = None
        ymax = None
        zmin = None
        zmax = None
        for obj in self.objs:
            for z in self.objs[obj]:
                if zmin is None or z < zmin: zmin = z
                if zmax is None or z > zmax: zmax = z
                for trace in self.objs[obj][z]:
                    for x, y in trace["points"]:
                        if xmin is None or x < xmin: xmin = x
                        if xmax is None or x > xmax: xmax = x
                        if ymin is None or y < ymin: ymin = y
                        if ymax is None or y > ymax: ymax = y
        
        return xmin, ymin, zmin, xmax, ymax, zmax

    def fillInSlices(self, volume : np.ndarray, zmin : int):
        """Fill in empty slices with the previous slice.
        
            Params:
                volume (np.ndarray): the volume to fill in
                zmin (int): the minimum z value
        """
        print(self.z_pos_list)
        for z in range(volume.shape[0]):
            print(z)
            if z + zmin in self.z_pos_list:
                slice = volume[z]
            else:
                volume[z] = slice

    def generateVolume(self, alpha : int = 100) -> np.ndarray:
        """Generate the numpy array volume.
        
            Params:
                alpha (int): opacity of the volume
        """
        xmin, ymin, zmin, xmax, ymax, zmax = self.getVolumeBounds()
        volume = np.zeros(
            (zmax-zmin+1, ymax-ymin+1, xmax-xmin+1, 4),
            dtype=np.ubyte
        )
        for obj in self.objs:
            for z in self.objs[obj]:
                for trace in self.objs[obj][z]:
                    pts = np.array(trace["points"])
                    pts[:,0] -= xmin
                    pts[:,1] -= ymin
                    cv2.fillPoly(
                        img=volume[z-zmin],
                        pts=[pts],
                        color=trace["color"] + [alpha]
                    )
        
        self.fillInSlices(volume, zmin)

        return volume

def tformScalePoints(points : list, t : list, mag : float) -> list[tuple[int]]:
    """Transform and scale a set of points.
    
        Params:
            points (list): the list of points
            t (list): the transform to apply
            mag (float): the magnification to apply
        Returns:
            (list[tuple[int]]): a list of points with the transform and mag applied
    """
    point_tform = QTransform(t[0], t[3], t[1], t[4], t[2], t[5])
    new_points = []
    for p in points:
        x, y = point_tform.map(*p)
        new_points.append((
            round(x / mag),
            round(y / mag)
        ))
    return new_points