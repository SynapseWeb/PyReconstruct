import os
import shutil
import numpy as np
import cv2
import zarr

from datetime import datetime
dt = None

from PyReconstruct.modules.datatypes import Series, Transform, Trace
from PyReconstruct.modules.backend.view import SectionLayer
from PyReconstruct.modules.backend.threading import ThreadPoolProgBar
from PyReconstruct.modules.calc import colorize, reducePoints

def setDT():
    """Set date and time."""
    global dt
    t = datetime.now()
    dt = f"{t.year}{t.month:02d}{t.day:02d}_{t.hour:02d}{t.minute:02d}{t.second:02d}"

def groupsToVolume(series: Series, groups: list=None, padding: float=None):
    """Convert objects in groups into a volume based on max and min x/y/section values.

        Params:
            group_name (str): group to include in zarr
            series (Series): a series object
            srange (tuple): the range of sections (exclusive)
            padding (float): padding (μm) to add around object
        Returns:
           [x position, y position, width, height], [start, end]
    """
    
    group_objects = []
    x_vals = []
    y_vals = []
    sec_range = set()
    
    if groups:
        for group in groups:
            group_objects += series.object_groups.getGroupObjects(group)

    print(f'group_objs: {group_objects}')
    
    for snum, section in series.enumerateSections():
        
        tform = section.tform

        # for each object to be included...

        for border_obj in group_objects:
        
            if border_obj in section.contours:
                
                xmin, ymin, xmax, ymax = section.contours[border_obj].getBounds(tform)

                sec_range.add(snum)
                x_vals += [xmin, xmax]
                y_vals += [ymin, ymax]

    x = min(x_vals)
    w = max(x_vals) - x
    y = min(y_vals)
    h = max(y_vals) - y

    sec_range = [min(sec_range), max(sec_range) + 1]

    if padding:
        x -= padding
        y -= padding
        w += (padding * 2)
        h += (padding * 2)

    window = [x, y, w, h]

    return window, sec_range


def createZarrName(window):
    """Return string representing a zarr file name"""

    window_str = [str(round(elem, 2)) for elem in window]
    return f'data_{"-".join(window_str)}.zarr'


def seriesToZarr(
        series : Series,
        srange : tuple,
        mag : float,
        window : list,
        data_fp: str = None,
        output_dir: str = None,
        other_attrs: dict = None,
):
    """Convert a series (images) into a neuroglancer-compatible zarr.
    
        Params:
            series (Series): the series to convert
            srange (tuple): the range of sections (exclusive)
            mag (float): the microns per pixel for the zarr file
            window (list): the window (x, y, height, width) for the resulting zarr
            data_fp (str): filename of output zarr
            output_dir (str): directory to store zarr
            other_attrs (dict): other infoformation to store in .zattrs

        Returns:
            the filepath for the zarr, the threadpool
    """

    # calculate field attributes
    shape = (
        srange[1] - srange[0],  # z
        round(window[3]/mag),   # height
        round(window[2]/mag)    # width
    )

    pixmap_dim = shape[2], shape[1]  # the w and h of a 2D array

    # create zarr files
    
    if not data_fp:  # if no data_fp provided, place with jser
        
        zarr_name = createZarrName(window)
        
        if not output_dir: output_dir = os.path.dirname(series.jser_fp)
            
        data_fp = os.path.join(output_dir, zarr_name)
        
    if os.path.isdir(data_fp): shutil.rmtree(data_fp)  # delete existing zarr
        
    data_zg = zarr.open(data_fp, "a")
    data_zg.create_dataset("raw", shape=shape, chunks=(1, 256, 256), dtype=np.uint8)

    # get values for saving zarr files (from last known section)
    section_thickness = series.loadSection(srange[0]).thickness
    z_res = round(section_thickness * 1000)
    xy_res = round(mag * 1000)
    resolution = [z_res, xy_res, xy_res]
    offset = [0, 0, 0]

    # get alignment of series
    alignment = {}
    for snum in range(*srange):
        alignment[str(snum)] = series.data["sections"][snum]["tforms"][series.alignment].getList()

    # save attributes
    data_zg["raw"].attrs["offset"] = offset
    data_zg["raw"].attrs["resolution"] = resolution 

    # save additional attributes for loading back into jser
    data_zg["raw"].attrs["window"] = window
    data_zg["raw"].attrs["srange"] = srange
    data_zg["raw"].attrs["true_mag"] = mag
    data_zg["raw"].attrs["alignment"] = alignment

    # save other info to root .zattrs
    if other_attrs:
        for k, v in other_attrs.items():
            data_zg.attrs[k] = v
    
    # create threadpool and interate through series
    threadpool = ThreadPoolProgBar()
    for snum in range(*srange):
        threadpool.createWorker(
            exportSection,
            data_zg,
            snum,
            series,
            srange,
            window,
            pixmap_dim
        )
    threadpool.startAll("Converting series to zarr...")

    return data_fp
    
def seriesToLabels(series : Series,
                   data_fp : str,
                   group : str = None):
    """Export contours as labels to an existing zarr.
    
        Params:
            series (Series): the series
            data_fp (str): the filepath for the zarr
            group (str): the group to export as labels (None if retraining)
    """
    # extract data from raw
    data_zg = zarr.open(data_fp)

    raw = data_zg["raw"]
    srange = raw.attrs["srange"]
    window = raw.attrs["window"]
    mag = raw.attrs["true_mag"]
    alignment = raw.attrs["alignment"]
    offset = raw.attrs["offset"]
    resolution = raw.attrs["resolution"]

    # calculate field attributes
    shape = (
        srange[1] - srange[0],
        round(window[3]/mag),
        round(window[2]/mag)
    )
    pixmap_dim = shape[2], shape[1]  # the w and h of the 2D array

    if group:
        is_group = True
        del_group = None
        group_or_tag = group
    # if retrain, use tag and search for group to delete
    else:
        is_group = False
        del_group = series.getRecentSegGroup()
        group_or_tag = f"{del_group}_keep"

    # create labels datasets
    data_zg.create_dataset(f"labels_{group_or_tag}", shape=shape, chunks=(1, 256, 256), dtype=np.uint64)
    data_zg[f"labels_{group_or_tag}"].attrs["offset"] = offset
    data_zg[f"labels_{group_or_tag}"].attrs["resolution"] = resolution

    # create threadpool
    threadpool = ThreadPoolProgBar()
    for snum in range(*srange):
        threadpool.createWorker(
            exportTraces,
            data_zg,
            snum,
            series,
            group_or_tag,
            is_group,
            srange,
            window,
            pixmap_dim,
            del_group,
            alignment[str(snum)]
        )
    threadpool.startAll("Converting contours to zarr...")

    # remove group-object associations
    if del_group:
        series.object_groups.removeGroup(del_group)


def labelsToObjects(series : Series, data_fp : str, group : str, labels : list = None):
    """Convert labels in a zarr file to objects in a series.
    
        Params:
            series (Series): the series to import zarr data into
            data_zg (str): the filepath for the zarr group
            group (str): the name of the group with labels of interest
            labels (list): the labels to import (will import all if None)
        Returns:
            the threadpool
    """
    data_zg = zarr.open(data_fp)
    srange = data_zg["raw"].attrs["srange"]

    # create threadpool and iterate through sections
    setDT()
    threadpool = ThreadPoolProgBar()
    for snum in range(*srange):
        threadpool.createWorker(
            importSection,
            data_zg,
            group,
            snum,
            series,
            labels
        )
    threadpool.startAll("Converting labels to contours...")

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

def exportSection(data_zg, snum : int, series : Series, srange : tuple, window : list, pixmap_dim : tuple):
    """Export the raw data for a single section.
    
        Params:
            data_zg: the zarr group
            snum (int): the section number
            series (Series): the series
            srange (tuple): the range of sections
            window (list): the frame for the raw export
            pixmap_dim (tuple): the w and h in pixels for the arr output
    """
    # print(f"Section {snum} exporting started")
    section = series.loadSection(snum)
    slayer = SectionLayer(section, series)
    z = snum - srange[0]

    arr = slayer.generateImageArray(
        pixmap_dim, 
        window
    )
    data_zg["raw"][z] = arr
    # print(f"Section {snum} exporting finished")

def exportTraces(data_zg,
                 snum : int,
                 series : Series,
                 group_or_tag : str,
                 is_group : bool,
                 srange : tuple,
                 window : list,
                 pixmap_dim : tuple,
                 del_group : str = None,
                 tform_list=None):
    """Export the traces as labels for a single section.
    
        Params:
            data_zg: the zarr group
            snum (int): the section number
            series (Series): the series
            group_or_tag (str): the group or tag to include as labels
            is_group (bool): True if the previous entry is a group, False if tag
            srange (tuple): the range of sections
            window (list): the frame for the raw export
            pixmap_dim (tuple): the w and h in pixels for the arr output
            del_group (str): the group to delete
            tform_list (list): the transform to apply to the traces
    """
    z = snum - srange[0]
    section = series.loadSection(snum)
    slayer = SectionLayer(section, series, load_image_layer=False)
    if tform_list:
        tform = Transform(tform_list)
    else:
        tform = None

    # gather the traces
    traces = []
    if is_group:
        group = group_or_tag
        for cname in series.object_groups.getGroupObjects(group):
            if cname in section.contours:
                traces += section.contours[cname].getTraces()
    else:
        tag = group_or_tag
        for cname in series.object_groups.getGroupObjects(del_group): # only search recent seg group to save time
            if cname in section.contours:
                for trace in section.contours[cname]:
                    if tag in trace.tags:
                        traces.append(trace)
    
    data_zg[f"labels_{group_or_tag}"][z] = slayer.generateLabelsArray(
            pixmap_dim,
            window,
            traces,
            tform=tform
    )

    # delete group if requested
    if not is_group:
        if del_group:
            for cname in series.object_groups.getGroupObjects(del_group):
                if cname in section.contours:
                    del(section.contours[cname])
            # add the traces of interest back in
            for trace in traces:
                trace.setHidden(True)
                section.addTrace(trace)
            section.save()

def importSection(data_zg, group, snum, series, ids=None):
    """Import label data for a single section.
    
        Params:
            data_zg: the zarr group
            group: the name of the zarr group with data to import
            snum (int): the section number
            series (Series): the series
            ids (list): the ids to include in importing
    """
    # get relevant information from zarr
    labels = data_zg[group]
    offset = labels.attrs["offset"]
    resolution = labels.attrs["resolution"]

    raw = data_zg["raw"]
    raw_resolution = raw.attrs["resolution"]
    window = raw.attrs["window"]
    srange = raw.attrs["srange"]
    mag = raw.attrs["true_mag"] / raw_resolution[-1] * resolution[-1]
    alignment = raw.attrs["alignment"]
    tform = Transform(alignment[str(snum)])

    # check if section was segmented
    z = snum - srange[0] - round(offset[0] / resolution[0])
    if not 0 <= z < labels.shape[0]:
        print(f"Section {snum} importing finished")
        return
    # load the section and data
    section = series.loadSection(snum)
    arr = labels[z]

    # exclude areas that already have good traces

    # get groups/tags that are good
    gts = []
    for zg in data_zg:
        if zg.startswith("labels_"):
            gts.append(zg[len("labels_"):])
        
    # gather traces with these groups or tags
    traces = []
    for trace in section.tracesAsList():
        for tag in trace.tags:
            if tag in gts:
                traces.append(trace)
                continue
        for g in gts:
            if trace.name in series.object_groups.getGroupObjects(g):
                traces.append(trace)
            
    # block out areas on the labels array with traces
    slayer = SectionLayer(section, series, load_image_layer=False)
    pixmap_dim = (arr.shape[1], arr.shape[0])

    # modify the window to adjust for offset and resolution
    zarr_window = window.copy()

    field_offset_x = offset[2] / resolution[2] * mag
    field_offset_y = offset[1] / resolution[1] * mag
    field_width = pixmap_dim[0] * mag
    field_height = pixmap_dim[1] * mag

    zarr_window[0] += field_offset_x
    zarr_window[1] += field_offset_y
    zarr_window[2] = field_width
    zarr_window[3] = field_height

    exclude_arr = slayer.generateLabelsArray(
        pixmap_dim,
        zarr_window,
        traces,
        tform
    )
    arr[exclude_arr != 0] = 0

    # iterate through label ids
    if ids is None:
        ids = np.unique(arr)
    for id in ids:
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
            trace_points = tform.map(ext.tolist(), inverted=True)          
            # create the trace and add to section
            trace = Trace(name=f"autoseg_{id}", color=tuple(map(int, colorize(id))))
            trace.points = trace_points
            trace.fill_mode = ("transparent", "unselected")
            section.addTrace(trace)
        # add trace to group
        series.object_groups.add(f"seg_{dt}", f"autoseg_{id}")

    section.save()
