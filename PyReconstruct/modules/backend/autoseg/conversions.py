import os
import shutil
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Union, List, Tuple

import cv2
import zarr

from PyReconstruct.modules.datatypes import Series, Transform, Trace
from PyReconstruct.modules.backend.view import SectionLayer
from PyReconstruct.modules.backend.threading import ThreadPoolProgBar
from PyReconstruct.modules.calc import colorize, reducePoints


dt = None


def setDT():
    """Set date and time."""
    global dt
    now = datetime.now()
    dt = now.strftime("%Y%m%d_%H%M%")


def get_offset(window, resolution, img_mag, relative_to, section_diff=0):
    """Calculate offset from a window."""

    lat, ax = window

    ul_all = (
        relative_to[0],
        relative_to[1] + relative_to[3]
    )

    ul_roi_group= (
        lat[0],
        lat[1] + lat[3]
    )

    ## do the things...

    scale_x = resolution[2] / 1000 / img_mag
    scale_y = resolution[1] / 1000 / img_mag

    x_diff_real = ul_roi_group[0] - ul_all[0]
    y_diff_real = ul_roi_group[1] - ul_all[1]

    x_diff_scaled = x_diff_real * scale_x
    y_diff_scaled = y_diff_real * scale_y

    x = round(x_diff_scaled * 1000)
    y = round(y_diff_scaled * 1000)
    
    z = section_diff * resolution[0]  # offset in z

    offset = [z, -y, x]

    return offset


def rechunk(
        zarr_fp: Union[str, Path],
        target_chunks: Tuple[int, int, int] = (8, 256, 256)
):
    """Rechunk all available datasets."""

    import dask.array as da

    if not isinstance(zarr_fp, Path):
        zarr_fp = Path(zarr_fp)
    
    z = zarr.open(str(zarr_fp), "r")

    for arr_name, src_arr in z.items():

        if not isinstance(src_arr, zarr.Array):
            continue

        src_fp = zarr_fp / arr_name
        target_fp = src_fp.with_name(arr_name + "_rechunked")
        
        da_old = da.from_zarr(src_fp)
        da_new = da_old.rechunk((8, 256, 256))
        
        da_new.to_zarr(target_fp)

        zarr.open(target_fp, "r+").attrs.update(src_arr.attrs)

        ## Remove original
        shutil.rmtree(str(src_fp))
        target_fp.rename(src_fp)
        
    return True


def groupsToVolume(series: Series, groups: list=None, padding: float=None, restrict_to_sections: list=None):
    """Convert objects in groups into a volume based on max and min x/y/section values.

        Params:
            group_name (str): group to include in zarr
            series (Series): a series object
            srange (tuple): the range of sections (exclusive)
            padding (float): padding (μm) to add around object
            restrict_to_sections (list): restrict volume to sections
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

    if restrict_to_sections:
        start, end = restrict_to_sections
        sec_range = [sec for sec in sec_range if sec >= start and sec <= end]
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


def seriesToZarr(series : Series,
                 sections : list,
                 mag : float,
                 window : list,
                 data_fp: str = None,
                 output_dir: str = None,
                 other_attrs: dict = None,
                 chunk_size: tuple = (1, 256, 256)):
    """Convert a series of images into a neuroglancer-compatible zarr.
    
        Params:
            series (Series): the series to convert
            sections (list): the sections to include (exclusive; ASSUME sorted already)
            mag (float): the microns per pixel for the zarr file
            window (list): the window (x, y, width, height) for the resulting zarr
            data_fp (str): filename of output zarr
            output_dir (str): directory to store zarr
            other_attrs (dict): other infoformation to store in .zattrs

        Returns:
            the filepath for the zarr, the threadpool
    """

    ## Calculate field attributes
    shape = (
        len(sections),  # z
        round(window[3]/mag),   # height
        round(window[2]/mag)    # width
    )

    pixmap_dim = shape[2], shape[1]  # the w and h of a 2D array

    ## Create zarr
    
    if not data_fp:  # if no data_fp provided, place with jser
        
        zarr_name = createZarrName(window)
        
        if not output_dir: output_dir = os.path.dirname(series.jser_fp)
            
        data_fp = os.path.join(output_dir, zarr_name)
        
    if os.path.isdir(data_fp): shutil.rmtree(data_fp)  # delete existing zarr
        
    data_zg = zarr.open(data_fp, "a")
    
    data_zg.create_dataset(
        "raw",
        shape=shape,
        chunks=chunk_size,
        dtype=np.uint8
    )

    ## Get values for saving zarr files (from last known section)
    section_thickness = series.loadSection(sections[0]).thickness
    z_res = int(section_thickness * 1000)
    xy_res = int(mag * 1000)
    resolution = [z_res, xy_res, xy_res]
    offset = [0, 0, 0]

    ## Get series alignment
    alignment = {}
    for snum in sections:
        current_tranform = series.data["sections"][snum]["tforms"][series.alignment].getList()
        alignment[str(snum)] = current_tranform

    # save attributes
    data_zg["raw"].attrs["offset"] = offset
    data_zg["raw"].attrs["voxel_size"] = resolution 
    data_zg["raw"].attrs["axis_names"] = ["z", "y", "x"]
    data_zg["raw"].attrs["units"] = ["nm", "nm", "nm"]

    # save additional attributes for loading back into jser
    data_zg["raw"].attrs["window"] = window
    data_zg["raw"].attrs["sections"] = sections
    data_zg["raw"].attrs["true_mag"] = mag
    data_zg["raw"].attrs["alignment"] = alignment

    # save other info to root .zattrs
    if other_attrs:
        for k, v in other_attrs.items():
            data_zg.attrs[k] = v
    
    # create threadpool and interate through series
    threadpool = ThreadPoolProgBar()
    
    for i, snum in enumerate(sections):
        threadpool.createWorker(
            exportSection,
            data_zg,
            snum,
            series,
            i,
            window,
            pixmap_dim
        )
        
    threadpool.startAll("Converting series to zarr...")

    return data_fp
    

def seriesToLabels(series: Series,
                   data_fp: str,
                   group: Union[str, None] = None,
                   window: Union[List, None] = None,
                   img_mag: float = 0.00254,
                   chunk_size: tuple = (1, 256, 256),
                   raw_window=Union[List, None],
                   section_diff: int=0):
    """Export contours as labels to an existing zarr.
    
        Params:
            series (Series): the series
            data_fp (str): the filepath for the zarr
            group (str): the group to export as labels (None if retraining)
    """

    # extract data from raw
    data_zg = zarr.open(data_fp)
    raw = data_zg["raw"]

    shape = raw.shape
    sections = list(range(*window[1]))
    mag = raw.attrs["true_mag"]
    alignment = raw.attrs["alignment"]
    resolution = raw.attrs["voxel_size"]

    if window:

        offset = get_offset(
            window,
            resolution,
            img_mag,
            relative_to=raw_window,
            section_diff=section_diff
        )
        
        window = window[0]

    else:

        window = raw.attrs["window"]
        offset = raw.attrs["offset"]

    # calculate field attributes
    shape = (
        len(sections),
        round(window[3] / mag),
        round(window[2] / mag)
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

    dataset_name = f"labels_{group_or_tag}"

    # create labels datasets
    data_zg.create_dataset(
        dataset_name,
        shape=shape,
        chunks=chunk_size,
        dtype=np.uint64
    )
    
    data_zg[dataset_name].attrs["offset"] = offset
    data_zg[dataset_name].attrs["voxel_size"] = resolution
    data_zg[dataset_name].attrs["axis_names"] = ["z", "y", "x"]
    data_zg[dataset_name].attrs["units"] = ["nm", "nm", "nm"]

    # create threadpool
    threadpool = ThreadPoolProgBar()

    for i, snum in enumerate(sections):
        threadpool.createWorker(
            exportTraces,
            data_zg,
            snum,
            series,
            group_or_tag,
            is_group,
            i,
            window,
            pixmap_dim,
            del_group,
            alignment[str(snum)]
        )

    threadpool.startAll("Converting contours to zarr...")

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
    if group not in data_zg:
        return
    
    sections = data_zg["raw"].attrs["sections"]

    # create threadpool and iterate through sections
    setDT()
    threadpool = ThreadPoolProgBar()
    for snum in sections:
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


def exportSection(data_zg,
                  snum : int,
                  series : Series,
                  z : int,
                  window : list,
                  pixmap_dim : tuple):
    """Export the raw data for a single section.
    
        Params:
            data_zg: the zarr group
            snum (int): the section number
            series (Series): the series
            z (int): the z-level of the section in the zarr
            window (list): the frame for the raw export
            pixmap_dim (tuple): the w and h in pixels for the arr output
    """
    # print(f"Section {snum} exporting started")
    section = series.loadSection(snum)
    slayer = SectionLayer(section, series)

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
                 z : int,
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
            z (int): the z position of the section in the zarr
            window (list): the frame for the raw export
            pixmap_dim (tuple): the w and h in pixels for the arr output
            del_group (str): the group to delete
            tform_list (list): the transform to apply to the traces
    """
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
    resolution = labels.attrs["resolution"]
    try:
        offset = labels.attrs["offset"]
    except KeyError:
        offset = [0, 0, 0]


    raw = data_zg["raw"]
    raw_resolution = raw.attrs["resolution"]
    try:
        raw_offset = raw.attrs["offset"]
    except KeyError:
        raw_offset = [0, 0, 0]

    window = raw.attrs["window"]
    sections = raw.attrs["sections"]
    mag = raw.attrs["true_mag"] / raw_resolution[-1] * resolution[-1]
    alignment = raw.attrs["alignment"]
    tform = Transform(alignment[str(snum)])

    # check if section was segmented
    z = sections.index(snum)
    if not 0 <= z < labels.shape[0]:
        print(f"Section {snum} importing finished")
        return
    # load the section and data
    section = series.loadSection(snum)
    arr = labels[z]
    
    pixmap_dim = (arr.shape[1], arr.shape[0])

    # modify the window to adjust for offset and resolution
    zarr_window = window.copy()

    field_offset_x = (offset[2] / resolution[2] - raw_offset[2] / raw_resolution[2]) * mag
    field_offset_y = (offset[1] / resolution[1] - raw_offset[2] / raw_resolution[2]) * mag
    field_width = pixmap_dim[0] * mag
    field_height = pixmap_dim[1] * mag

    zarr_window[0] += field_offset_x
    zarr_window[1] += field_offset_y
    zarr_window[2] = field_width
    zarr_window[3] = field_height

    # # exclude areas that already have good traces (TEMPORARILY REMOVED)

    # # get groups/tags that are good
    # gts = []
    # for zg in data_zg:
    #     if zg.startswith("labels_"):
    #         gts.append(zg[len("labels_"):])
        
    # # gather traces with these groups or tags
    # traces = []
    # for trace in section.tracesAsList():
    #     for tag in trace.tags:
    #         if tag in gts:
    #             traces.append(trace)
    #             continue
    #     for g in gts:
    #         if trace.name in series.object_groups.getGroupObjects(g):
    #             traces.append(trace)

    # slayer = SectionLayer(section, series, load_image_layer=False)
    # exclude_arr = slayer.generateLabelsArray(
    #     pixmap_dim,
    #     zarr_window,
    #     traces,
    #     tform
    # )
    # arr[exclude_arr != 0] = 0

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


def zarrToNewSeries(zarr_fp : str, label_groups : list, name : str):
    """Create a new series from a neuroglancer zarr.
    
        Params:
            zarr_fp (str): the filepath to the full neuroglancer zarr file
            label_groups (str): the list of label groups to include as contours
            name (str): the name of the new series
    """
    ng_zarr = zarr.open(zarr_fp, "r+")

    ## Assume "raw" exists
    raw = ng_zarr["raw"]

    ## Save the original attributes
    original_attr_items = []

    ## These modified while making new series
    for k in ("window", "sections", "alignment"):
        try:
            original_attr_items.append((k, raw.attrs[k]))
        except KeyError:
            pass

    ## Set magnification
    if "true_mag" in raw.attrs:
        
        true_mag = raw.attrs["true_mag"]
        
    elif "resolution" in raw.attrs:
        
        true_mag = raw.attrs["resolution"][-1]
        raw.attrs["true_mag"] = true_mag

    else:  # no resolution provided

        true_mag = 4  # default to lat res of 4x4
        raw.attrs["true_mag"] = true_mag

    ## Set window
    z, y, x = raw.shape
    window = [0, 0, x * true_mag, y * true_mag]
    raw.attrs["window"] = window

    ## Set the sections
    sections = list(range(z))
    digits = len(str(sections[-1]))
    raw.attrs["sections"] = sections

    ## Set alignment
    alignment = {}
    for snum in sections:
        alignment[str(snum)] = Transform.identity().getList()
    raw.attrs["alignment"] = alignment

    ## Get thickness
    thickness = raw.attrs["resolution"][0] / 1000  # nm -> μm

    ## Create zarr containing the images
    ## (i.e., split out each section into a new individual group)

    images_dir = Path(zarr_fp).with_name(f"{name}_images.zarr")
    print(images_dir)

    images_zarr = zarr.open(images_dir, "w-")
    images_zarr.create_group("scale_1")
    images = images_zarr["scale_1"]
    image_locations = []

    for i, snum in enumerate(sections):

        src = f"section{snum:0{digits}d}"
        print(f"Woring on {src}...")

        images.create_dataset(src, data=raw[i])

        img_loc = os.path.join(images_dir, "scale_1", src)
        print(img_loc)
        image_locations.append(img_loc)
    
    # create the new series
    series = Series.new(
        image_locations,
        name,
        true_mag,
        thickness
    )

    # import the label data into the series
    for label_group in label_groups:
        if label_group in ng_zarr:
            labelsToObjects(
                series,
                zarr_fp,
                label_group,
            )
    
    # reset the original attributes for the raw
    for key, value in original_attr_items:
        raw.attrs[key] = value

    
    # return the series
    return series

