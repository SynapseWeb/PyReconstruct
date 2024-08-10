#!/usr/bin/env python

"""Create neuroglancer-formatted zarrs from PyReconstruct jser files."""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone
import zarr
import cv2

from PySide6.QtWidgets import QApplication

from PyReconstruct.modules.datatypes import Series

from PyReconstruct.modules.backend.autoseg import (
    seriesToZarr,
    seriesToLabels,
    groupsToVolume,
    rechunk
)

from PyReconstruct.assets.scripts.create_ng_zarr.parser import (
    get_args,
    parse_args
)

from PyReconstruct.assets.scripts.create_ng_zarr.utils import (
    print_flush,
    flatten_list,
    get_sha1sum,
    print_summary
)


args = get_args()
jser_fp, output_zarr, start, end, mag, padding, max_tissue = parse_args(args)

print_flush("Opening series...")

series = Series.openJser(jser_fp)

print_flush("Gathering args...")

groups = flatten_list(args.groups) if args.groups else None

all_sections = sorted(list(series.sections.keys()))

if start is None: start = all_sections[1]  # steer clear of cal grid
if end is None: end = all_sections[-1]

srange = (start, end + 1)

sections = []
for n in sorted(list(series.sections.keys())):
    if start <= n <= end:
        sections.append(n)

## Sample a section and get img mag and dim
## Assume all sections same dim for now

section = series.loadSection(sections[0])
img_mag = section.mag

## TODO: Validate Zarr container more appropriately
if series.src_dir.endswith("zarr"):

    img_scale_1 = os.path.join(series.src_dir, "scale_1", section.src)
    h, w = zarr.open(img_scale_1).shape

else:

    img_fp = os.path.join(series.src_dir, section.src)
    h, w, _ = cv2.imread(img_fp).shape


img_corners = [(0, 0), (w, 0), (w, h), (0, h)]

convert_microns = lambda x: x * img_mag
img_corners = [list(map(convert_microns, elem)) for elem in img_corners]

## Determine if req for all tissue or crop
get_all = (bool(max_tissue) or not bool(groups))

## Procedures

if get_all:  # request all available (include possible black space)

    x_mins, y_mins, x_maxs, y_maxs = ([], [], [], [])

    for section in sections:

        sec_tform = series.loadSection(section).tform
        corners_transformed = sec_tform.map(img_corners)

        x_vals, y_vals = list(zip(*corners_transformed))

        x_mins.append(min(x_vals))
        y_mins.append(min(y_vals))
        
        x_maxs.append(max(x_vals))
        y_maxs.append(max(y_vals))

    window = [
        min(x_mins),
        min(y_mins),
        max(x_maxs) - min(x_mins),
        max(y_maxs) - min(y_mins),
    ]

else:  # request zarr around group(s)

    if padding:
        padding *= img_mag  # convert padding from to μm
        
    window, _ = groupsToVolume(series, groups, padding)

additional_attrs = {
        "filepath": str(Path(jser_fp).absolute()),
        "sha1sum": get_sha1sum(jser_fp),
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d, %H:%M:%S")
    }

print_flush("Initializing pyqt...")

if not QApplication.instance():

    print_flush("Creating QApplication instance...")
    app = QApplication(sys.argv)

print_flush("Creating zarr...")

zarr_fp = seriesToZarr(
    series,
    sections,
    img_mag,
    window=window,
    data_fp=output_zarr,
    other_attrs=additional_attrs
)

# Add labels to zarr if object groups provided
if groups:

    padding *= img_mag
    window_groups = groupsToVolume(series, groups, padding)

    for group in groups:

        print_flush(f"Converting group {group} to labels...")
        seriesToLabels(
            series,
            zarr_fp,
            group,
            window=window_groups,
            img_mag=img_mag,
            raw_window=window
        )

series.close()

print_flush("Rechunking datasets...")

try:

    rechunk(zarr_fp)

except ValueError:

    print_flush("Rechunking not possible.")

print_summary(series, window, start, end, mag, zarr_fp)
