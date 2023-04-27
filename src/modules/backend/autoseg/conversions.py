import os
import shutil
import numpy as np
import cv2
import zarr

from modules.datatypes import Series, Transform, Trace
from modules.backend.view import SectionLayer
from modules.backend.threading import ThreadPool
from modules.calc import colorize, reducePoints

def seriesToZarr(
        series : Series,
        groups : list[str],
        border_obj : str,
        srange : tuple,
        mag : float,
        finished_fn=None,
        update=None):
    """Convert a series into a zarr file usable by neuroglancer.
    
        Params:
            series (Series): the series to convert
            groups (list[str]): the group names to include in the zarr as labels
            border_obj (str): the object to use as the border marking
            srange (tuple): the range of sections (exclusive)
            mag (float): the microns per pixel for the zarr file
            finished_fn (function): the function to run when finished
            update (function): the function to update a progress bar
        Returns:
            the filepath for the zarr, the threadpool
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
    if os.path.isdir(data_fp):  # delete existing data.zarr
        shutil.rmtree(data_fp)
    data_zg = zarr.open(data_fp, "a")
    data_zg["raw"] = zarr.empty(shape=shape, chunks=(1, 256, 256), dtype=np.uint8)
    for group in groups:
        data_zg[f"labels_{group}"] = zarr.empty(shape=shape, chunks=(1, 256, 256), dtype=np.uint64)
    
    # create threadpool and interate through series
    threadpool = ThreadPool(update=update)
    for snum in range(*srange):
        threadpool.createWorker(
            export_section,
            data_zg,
            snum,
            series,
            groups,
            srange,
            window,
            pixmap_dim
        )
    threadpool.startAll(finished_fn, data_fp)
    
    # get values for saving zarr files (from last known section)
    z_res = round(section.thickness * 1000)
    xy_res = round(mag * 1000)
    resolution = [z_res, xy_res, xy_res]
    offset = [0, 0, 0]

    # get alignment of series
    alignment = {}
    for snum in range(*srange):
        alignment[str(snum)] = series.section_tforms[snum][series.alignment].getList()

    # save attributes
    data_zg["raw"].attrs["offset"] = offset
    data_zg["raw"].attrs["resolution"] = resolution 

    # save additional attributes for loading back into jser
    data_zg["raw"].attrs["window"] = window
    data_zg["raw"].attrs["srange"] = srange
    data_zg["raw"].attrs["true_mag"] = mag
    data_zg["raw"].attrs["alignment"] = alignment

    for group in groups:
        data_zg[f"labels_{group}"].attrs["offset"] = offset
        data_zg[f"labels_{group}"].attrs["resolution"] = resolution

        data_zg[f"labels_{group}"].attrs["window"] = window
        data_zg[f"labels_{group}"].attrs["srange"] = srange
        data_zg[f"labels_{group}"].attrs["true_mag"] = mag
        data_zg[f"labels_{group}"].attrs["alignment"] = alignment
    
    return threadpool  # pass the threadpool to keep in memory

def labelsToObjects(series : Series, data_fp : str, group : str, finished_fn=None, update=None):
    """Convert labels in a zarr file to objects in a series.
    
        Params:
            series (Series): the series to import zarr data into
            data_zg (str): the filepath for the zarr group
            group (str): the name of the group with labels of interest
            finished_fn (function): the function to run when finished
            update (function): the function to update a progress bar
        Returns:
            the threadpool
    """
    data_zg = zarr.open(data_fp)
    srange = data_zg["raw"].attrs["srange"]

    # create threadpool and iterate through sections
    threadpool = ThreadPool(update=update)
    for snum in range(*srange):
        threadpool.createWorker(
            import_section,
            data_zg,
            group,
            snum,
            series
        )
    threadpool.startAll(finished_fn)
    
    return threadpool  # pass the threadpool to keep in memory

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

def export_section(data_zg, snum, series, groups, srange, window, pixmap_dim):
    print(f"Section {snum} exporting started")
    section = series.loadSection(snum)
    slayer = SectionLayer(section, series)
    z = snum - srange[0]
    arr = slayer.generateImageArray(
        pixmap_dim, 
        window
    )
    data_zg["raw"][z] = arr

    for group in groups:
        data_zg[f"labels_{group}"][z] = slayer.generateLabelsArray(
            pixmap_dim,
            window,
            series.object_groups.getGroupObjects(group)
        )
    print(f"Section {snum} exporting finished")

def import_section(data_zg, group, snum, series):
    print(f"Section {snum} importing started")
    # get relevant information from zarr
    labels = data_zg[group]
    offset = labels.attrs["offset"]
    resolution = labels.attrs["resolution"]

    raw = data_zg["raw"]
    window = raw.attrs["window"]
    srange = raw.attrs["srange"]
    mag = raw.attrs["true_mag"]
    alignment = raw.attrs["alignment"]

    # check if section was segmented
    z = snum - srange[0] - round(offset[0] / resolution[0])
    if not 0 <= z < labels.shape[0]:
        print(f"Section {snum} importing finished")
        return
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
            # create the trace and add to section
            trace = Trace(name=str(id), color=tuple(map(int, colorize(id))))
            trace.points = trace_points
            trace.fill_mode = ("transparent", "unselected")
            section.addTrace(trace, log_message="Imported from autoseg data")
    section.save()
    print(f"Section {snum} importing finished")
