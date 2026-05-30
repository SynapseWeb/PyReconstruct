import os
import re
import sys
import zarr
import numpy as np

# add src modules to the system path
sys.path.append(os.path.join(os.getcwd(), "..", ".."))
from PyReconstruct.modules.datatypes import Series

def cropZarr(series_fp : str, obj_name : str, radius : float, src_dir : str = ""):
    """Crop the zarr file for a series.

        Params:
            series_fp (str): the filepath for the series jser
            obj_name (str): the name of the object to crop around
            radius (float): the radius of the crop
            src_dir (str): optional path to the source zarr; if blank, the
                location stored in the series is used. An override must point
                to the same zarr (same scale_N groups and per-section array
                names), just at a different location.
    """
    # open the series and check that it uses a zarr file
    series = Series.openJser(series_fp)
    # use the override if given, otherwise the location stored in the series
    src_dir = (src_dir or series.src_dir).rstrip("/\\")  # normalize trailing separators

    # recognize zarr directories whose "zarr" suffix uses any common
    # separator, e.g. "foo.zarr", "foo-zarr", or "foo_zarr"
    basename = os.path.basename(src_dir)
    match = re.match(r"^(?P<stem>.+)(?P<sep>[.\-_])(?P<ext>zarr)$", basename, re.IGNORECASE)
    if not match:
        raise Exception(
            f"This series does not use a zarr file for its images (src_dir={series.src_dir!r})."
        )

    # set up the new zarr folder, preserving the original separator/suffix style
    zarr_name = match.group("stem")
    zarr_sep = match.group("sep")
    zarr_ext = match.group("ext")
    new_zarr_fp = os.path.join(
        os.path.dirname(src_dir),
        f"{zarr_name}_{obj_name}_crop{zarr_sep}{zarr_ext}"
    )

    # the images live under scale_N groups (multiscale zarr); discover them
    src_group = zarr.open(src_dir, mode="r")
    scales = sorted(
        int(name.split("_")[1])
        for name in src_group.group_keys()
        if name.startswith("scale_") and name.split("_")[1].isnumeric()
    )
    if not scales:
        raise Exception(f"No scale_N groups found in {src_dir!r}.")

    new_group = zarr.open(new_zarr_fp, mode="a")

    # iterate through the sections
    for snum, section in series.enumerateSections(
        message="Cropping images..."
    ):
        # the section bounds are in microns; section.mag is the scale_1 resolution
        if obj_name in section.contours:
            xmin, ymin, xmax, ymax = section.contours[obj_name].getBounds()
        else:
            xmin = ymin = xmax = ymax = None  # blank image on this section

        # crop the image at every scale level
        for scale in scales:
            scale_grp = f"scale_{scale}"
            if section.src not in src_group[scale_grp]:
                continue
            image = src_group[scale_grp][section.src]
            cropped = np.zeros(image.shape, dtype=image.dtype)

            if xmin is not None:
                # resolution of this scale level (scale_1 mag scaled by factor)
                mag = section.mag * scale
                l = max(round((xmin - radius) / mag), 0)
                r = min(round((xmax + radius) / mag), image.shape[1])
                b = min(round(image.shape[0] - ((ymin - radius) / mag)), image.shape[0])
                t = max(round(image.shape[0] - ((ymax + radius) / mag)), 0)
                cropped[t:b, l:r] = image[t:b, l:r]

            out = new_group.require_group(scale_grp)
            out.create_dataset(
                section.src,
                data=cropped,
                chunks=image.chunks,
                dtype=image.dtype,
                overwrite=True,
            )

    series.close()

jser_fp = input("Jser filepath: ")
obj_name = input("Object name to crop around: ")
radius = float(input("Radius around BOUNDARY of object to include: "))
src_dir = input("Zarr location (leave blank to use the location stored in the series): ").strip()

cropZarr(jser_fp, obj_name, radius, src_dir)
