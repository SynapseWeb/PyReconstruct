import cv2
import numpy as np

import pyqtgraph.opengl as gl

from modules.pyrecon.series import Series

from modules.gui.gui_functions import progbar

class ObjectVolume():

    def __init__(self, series : Series, obj_names : list[str]):
        """Load the objects in a series.
        
            Params:
                series (Series): the series object
                obj_names (list[str]): the list of object names to gather data for
        """
        # create objects dictionary
        self.obj_data = {}

        # check section thickness
        self.section_thickness = None
        self.uniform_section_thickness = True

        # create loading bar
        update, canceled = progbar("3D", "Loading data...")
        final_value = len(series.sections)
        progress = 0
        self.canceled = False
        
        # iterate through all the sections and gather traces
        for snum in series.sections:
            # load the section
            self.obj_data[snum] = {}
            section = series.loadSection(snum)

            # check section thickness (is it uniform?)
            self.obj_data[snum]["thickness"] = section.thickness
            if self.section_thickness is None:
                self.section_thickness = section.thickness
            elif abs(self.section_thickness - section.thickness) > 1e-6:
                self.uniform_section_thickness = False
            
            # load the object points
            self.obj_data[snum]["contours"] = {}
            for obj_name in obj_names:
                self.obj_data[snum]["contours"][obj_name] = []
                # check if object exists in section
                if obj_name not in section.contours:
                    continue
                # transform points and add them to list
                for trace in section.contours[obj_name]:
                    modified_points = section.tforms[series.alignment].map(trace.points)
                    self.obj_data[snum]["contours"][obj_name].append({
                        "points" : modified_points,
                        "color" : trace.color
                    })
            
            # update the progress
            progress += 1
            update(progress/final_value*100)
            if canceled():
                self.canceled = True
                return

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
        for z in self.obj_data:
            z_checked = False
            for contour in self.obj_data[z]["contours"]:
                for trace in self.obj_data[z]["contours"][contour]:
                    # only check for z if traces exist
                    if not z_checked:
                        if zmin is None or z < zmin: zmin = z
                        if zmax is None or z > zmax: zmax = z
                        z_checked = True
                    for x, y in trace["points"]:
                        if xmin is None or x < xmin: xmin = x
                        if xmax is None or x > xmax: xmax = x
                        if ymin is None or y < ymin: ymin = y
                        if ymax is None or y > ymax: ymax = y
        
        return xmin, ymin, zmin, xmax, ymax, zmax

    def fillInSlices(self, volume : np.ndarray, z_slices : list):
        """Fill in empty slices with the previous slice.
        
            Params:
                volume (np.ndarray): the volume to fill in
                zmin (int): the minimum z value
        """
        # empty slices will exist if non-uniform section thickness
        for z in range(volume.shape[0]):
            if z in z_slices:
                slice = volume[z]
            else:
                volume[z] = slice

    def generateVolume(self, volume_threshold : int = 1e7, alpha : int = 255) -> tuple[gl.GLVolumeItem, tuple, tuple]:
        """Generate the numpy array volume.
        
            Params:
                volume_threshold (int): the max possible volume (higher number = higher res, but slower)
                alpha (int): opacity of the volume
            Returns:
                (gl.GLVolumeItem): the volume item (scaled to micron size)
                (size): the z, y, x size of the volume (scaled to micron size)
                (offset): the z, y, x offset of the object (in microns)
        """
        # if section thickness is not uniform:
        # modify the object data so that section number is converted to microns
        if not self.uniform_section_thickness:
            zs_obj_data = {}
            for snum in self.obj_data:
                st = self.obj_data[snum]["thickness"]
                zs_obj_data[snum * st] = self.obj_data[snum]
            self.obj_data = zs_obj_data

        # get the minimum and maximum x, y, z
        xmin, ymin, zmin, xmax, ymax, zmax = self.getVolumeBounds()

        # calculate the desired maginification based on the final volume
        if self.uniform_section_thickness:
            mag = (volume_threshold / ((zmax-zmin+1) * (ymax-ymin+1) * (xmax-xmin+1)))**(1/2)
            vshape = (zmax-zmin+1, int(mag*(ymax-ymin)+1), int(mag*(xmax-xmin)+1), 4)
        else:
            mag = (volume_threshold / ((zmax-zmin+1) * (ymax-ymin+1) * (xmax-xmin+1)))**(1/3)
            vshape = (int(mag*(zmax-zmin)+1), int(mag*(ymax-ymin)+1), int(mag*(xmax-xmin)+1), 4)
        
        # create the volume
        volume = np.zeros(vshape, dtype=np.ubyte)
        
        # add the contours to the array
        if not self.uniform_section_thickness:  # keep track of z slices if not uniform
            z_slices = []
        for z in self.obj_data:
            for contour in self.obj_data[z]["contours"]:
                for trace in self.obj_data[z]["contours"][contour]:
                    # scale and translate xy points
                    pts = np.array(trace["points"]) * mag
                    pts[:,0] -= xmin * mag
                    pts[:,1] -= ymin * mag
                    pts = pts.astype(np.int32)
                    # get z position
                    if self.uniform_section_thickness:
                        z_slice = z - zmin
                    else:
                        z_slice = int(z*mag - zmin*mag)
                        z_slices.append(z_slice)
                    # plot the trace
                    cv2.fillPoly(
                        img=volume[z_slice],
                        pts=[pts],
                        color=trace["color"] + [alpha]
                    )
        
        # fill in the volume if non-uniform section thickness
        if not self.uniform_section_thickness:
            self.fillInSlices(volume, z_slices)
        
        # guide lines (xyz : rgb)
        # volume[:,0,0] = [0, 0, 255, 255]
        # volume[0,:,0] = [0, 255, 0, 255]
        # volume[0,0,:] = [255, 0, 0, 255]

        # create the volume item
        vol_item = gl.GLVolumeItem(volume)

        # scale the volume item to fit actual micron size
        if self.uniform_section_thickness:
            xs = 1 / mag
            ys = 1 / mag
            zs = self.section_thickness  # match section thickness
        else:
            xs = 1 / mag
            ys = 1 / mag
            zs = 1 / mag
        vol_item.scale(zs, ys, xs)
        
        # get the shape of the object
        z, y, x, _ = volume.shape

        if self.uniform_section_thickness:
            zmin *= self.section_thickness
        
        return (
            vol_item,
            (z*zs, y*ys, x*xs),
            (zmin, ymin, xmin)
        )