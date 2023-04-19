import os
import numpy as np
import cv2
import random
import zarr

from modules.datatypes import Series, Transform, Trace
from modules.backend.view import SectionLayer
from modules.backend.func import reducePoints

def seriesToZarr(
        series : Series,
        groups : list[str],
        border_obj : str,
        srange : tuple,
        mag : float):
    """Convert a series into a zarr file usable by neuroglancer.
    
        Params:
            series (Series): the series to convert
            groups (list[str]): the group names to include in the zarr as labels
            border_obj (str): the object to use as the border marking
            srange (tuple): the range of sections (exclusive)
            mag (float): the microns per pixel for the zarr file
    """
    # get the border window
    x_vals = []
    y_vals = []
    for snum in range(*srange):
        section = series.loadSection(snum)
        tform = section.tforms[series.alignment]
        if border_obj in section.contours:
            xmin, ymin, xmax, ymax = section.contours[border_obj].getBounds(tform)
            x_vals += [xmin, xmax]
            y_vals += [ymin, ymax]
    x = min(x_vals)
    w = max(x_vals) - x
    y = min(y_vals)
    h = max(y_vals) - y
    window = [x, y, w, h]

    # calculate field attributes
    shape = (
        srange[1] - srange[0],
        round(window[3]/mag),
        round(window[2]/mag)
    )
    pixmap_dim = shape[2], shape[1]  # the w and h of a 2D array

    # create the zarr files
    data_fp = os.path.join(
        os.path.dirname(series.jser_fp),
        "data.zarr"
    )
    data_zg = zarr.open(data_fp)
    raw_zarr = data_zg.zeros("raw", shape=shape, dtype=np.uint8)
    labels_zarrs = {}
    for group in groups:
        labels_zarrs[group] = data_zg.zeros(f"labels_{group}", shape=shape, dtype=np.uint32)
    
    # iterate through series
    alignment = {}
    for snum in range(*srange):
        section = series.loadSection(snum)
        slayer = SectionLayer(section, series)
        z = snum - srange[0]
        raw_zarr[z] = slayer.generateImageArray(
            pixmap_dim, 
            window
        )
        for group in groups:
            labels_zarrs[group][z] = slayer.generateLabelsArray(
                pixmap_dim,
                window,
                series.object_groups.getGroupObjects(group)
            )
        alignment[str(snum)] = section.tforms[series.alignment].getList()

    # get values for saving zarr files (from last known section)
    z_res = int(section.thickness * 1000)
    xy_res = int(mag * 1000)
    resolution = [z_res, xy_res, xy_res]
    offset = [0, 0, 0]

    # save attributes
    raw_zarr.attrs["offset"] = offset
    raw_zarr.attrs["resolution"] = resolution

    for group in groups:
        labels_zarrs[group].attrs["offset"] = offset
        labels_zarrs[group].attrs["resolution"] = resolution

    # save additional attributes for loading back into jser
    raw_zarr.attrs["window"] = window
    raw_zarr.attrs["srange"] = srange
    raw_zarr.attrs["true_mag"] = mag
    raw_zarr.attrs["alignment"] = alignment

    for group in groups:
        labels_zarrs[group].attrs["window"] = window
        labels_zarrs[group].attrs["srange"] = srange
        labels_zarrs[group].attrs["true_mag"] = mag
        labels_zarrs[group].attrs["alignment"] = alignment
    
    return data_fp

def getExteriors(mask : np.ndarray) -> list[np.ndarray]:
    """Get the exteriors from a mask.
    
        Params:
            mask (np.ndarray): the mask to extract exteriors from
        Returns:
            (list[np.ndarray]): the list of exteriors
    """
    cv_detected, hierarchy = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    exteriors = []
    for e in cv_detected:
        e = e[:,0,:]
        # invert the y axis
        e[:,1] *= -1
        e[:,1] += mask.shape[0]
        # reduce the points
        e = reducePoints(e, array=True)
        exteriors.append(e)
    return exteriors

def randomColor():
    """Return a random color (rgb or primary)."""
    r = random.randint(1, 6)
    if r == 1:
        return (255, 0, 0)
    elif r == 2:
        return (0, 255, 0)
    elif r == 3:
        return (0, 0, 255)
    elif r == 4:
        return (0, 255, 255)
    elif r == 5:
        return (255, 0, 255)
    elif r == 6:
        return (255, 255, 0)

def labelsToObjects(series : Series, labels_fp):
    """Convert labels in a zarr file to objects in a series.
    
        Params:
            series (Series): the series to import zarr data into
            labels (zarr): the labels zarr object
    """
    labels = zarr.open(labels_fp)
    raw = zarr.open(os.path.join(
        os.path.dirname(labels_fp),
        "raw"
    ))

    # get relevant information from zarr
    offset = labels.attrs["offset"]
    resolution = labels.attrs["resolution"]

    window = raw.attrs["window"]
    srange = raw.attrs["srange"]
    mag = raw.attrs["true_mag"]
    alignment = raw.attrs["alignment"]

    colors = {}  # store colors for each id/object
    for snum in range(*srange):
        # check if section was segmented
        z = snum - srange[0] - round(offset[0] / resolution[0])
        if not 0 <= z < labels.shape[0]:
            continue
        # load the section and data
        section = series.loadSection(snum)
        arr = labels[z]
        # iterate through unique labels
        for id in np.unique(arr):
            if id == 0:
                continue
            # get exteriors for the label
            exteriors = getExteriors(arr == id)
            for ext in exteriors:
                # convert to float
                ext = ext.astype(np.float64)
                # add offset to coordinates
                ext[:,0] += offset[2] / resolution[2]
                ext[:,1] += offset[1] / resolution[1]
                # scale to actual coordinates
                ext *= mag
                # add origin
                ext[:,0] += window[0]
                ext[:,1] += window[1]
                # apply reverse transform
                tform = Transform(alignment[str(snum)])
                trace_points = tform.map(ext.tolist(), inverted=True)
                # get the trace color
                if id not in colors:
                    colors[id] = randomColor()
                c = colors[id]               
                # create the trace and add to section
                trace = Trace(name=str(id), color=c)
                trace.points = trace_points
                section.addTrace(trace, log_message="Imported from autoseg data")
        section.save()