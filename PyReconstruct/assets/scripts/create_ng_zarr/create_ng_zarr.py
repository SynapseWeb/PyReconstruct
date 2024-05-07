#!/usr/bin/env python

"""Create neuroglancer-formatted zarrs from PyReconstruct jser files."""

import sys
import os
from pathlib import Path
import zarr
import subprocess
import argparse
import tomllib
import cv2

from PySide6.QtWidgets import QApplication

# Imports are a nightmare (set repo root here)
project_dir = Path(__file__).parents[4]
sys.path.append(str(project_dir))

from PyReconstruct.modules.datatypes import Series
from PyReconstruct.modules.backend.autoseg import (
    seriesToZarr,
    seriesToLabels,
    groupsToVolume,
)


parser = argparse.ArgumentParser(
    prog="ng-create-zarr",
    description=__doc__,
    epilog="example call: ng-create-zarr my_series.jser --groups dendrites spines",
)

# poitional args
parser.add_argument("jser", type=str, nargs="?", help="Filepath of a valid jser file.")

# optional args

parser.add_argument(
    "--config",
    "-c",
    type=str,
    help="filepath to a toml config file"
)

## parser.add_argument("--height", "-y", type=float, default=2.0, help='height in μm (default %(default)s μm)')

## parser.add_argument("--width", "-x", type=float, default=2.0, help='width in μm (default %(default)s μm)')

parser.add_argument(
    "--sections",
    "-s",
    type=int,
    default=50,
    help="number of sections to include (default %(default)s sections)",
)

parser.add_argument(
    "--mag",
    "-m",
    type=float,
    default=0.008,
    help="output zarr mag in μm/vox (default %(default)s μm/vox)",
)

## parser.add_argument("--obj", "-o", type=str, help='object used to define a zarr window')

parser.add_argument(
    "--output",
    "-o",
    type=str,
    default=None,
    help="Optional output path",
)

parser.add_argument(
    "--padding",
    "-p",
    type=int,
    default=50,
    help="padding (px) to include around an object (default %(default)s px)",
)

parser.add_argument(
    "--groups",
    "-g",
    type=str,
    action="append",
    nargs="*",
    default=None,
    help="PyReconstruct object groups to include as labels (default %(default)s μm/vox)",
)

parser.add_argument(
    "--max_tissue",
    action="store_true",
    help="Inclue all possible tissue and black space",
)

# parser.add_argument("--min_tissue", action='store_true', help='Crop images to include only tissue')

args = parser.parse_args()

# Change defaults according to optional toml config file
if args.config:
    with open(args.config, "rb") as fp:
        try:
            parser.set_defaults(**tomllib.load(fp))
        except tomllib.TOMLDecodeError:
            parser.error("Malformed toml config file.")
    if args.groups:
        parser.set_defaults(
            groups=None
        )  # override toml acting as defaults if --groups called
    args = parser.parse_args()

# Make sure "valid" jser provided
if not args.jser or not os.path.exists(args.jser):
    parser.error("Please provide filepath to a valid jser.")

jser_fp = args.jser
output_zarr = args.output
# h_out    = float(args.height)
# w_out    = float(args.width)
secs = int(args.sections)
mag = float(args.mag)
padding = int(args.padding)
get_all = bool(args.max_tissue)


def flatten_list(nested_list):
    """Recursively flatten lists to handle groups."""

    if not (bool(nested_list)):  # if empty list
        return nested_list

    if isinstance(nested_list[0], list):

        return flatten_list(*nested_list[:1]) + flatten_list(nested_list[1:])

    return nested_list[:1] + flatten_list(nested_list[1:])


groups = flatten_list(args.groups) if args.groups else None

print("Opening series...")
series = Series.openJser(jser_fp)

print("Gathering args...")
sections = sorted(list(series.sections.keys()))

## Sample a section to get image magnification and dimensions
## Assume all sections have the same dimensions for now

section = series.loadSection(sections[1])  # steer clear of cal grid
img_mag = section.mag

if series.src_dir.endswith("zarr"):  ## TODO: Need to validate zarrs more appropriately

    img_scale_1 = os.path.join(series.src_dir, "scale_1", section.src)
    h, w = zarr.open(img_scale_1).shape

else:

    img_fp = os.path.join(series.src_dir, section.src)
    h, w, _ = cv2.imread(img_fp).shape

convert_microns = lambda x: x * img_mag
img_corners = [(0, 0), (w, 0), (h, w), (0, h)]
img_corners = [list(map(convert_microns, elem)) for elem in img_corners]

## Procedures

get_most = None

if get_all:  # request all available (include black space)

    mid = len(sections) // 2
    start = mid - (secs // 2) - 1
    end_exclude = mid + (secs // 2) - 1

    srange = (sections[start], sections[end_exclude])

    x_mins, y_mins, x_maxs, y_maxs = ([], [], [], [])

    for section in range(srange[0], srange[1]):

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
        max(y_maxs) - min(y_mins),
        max(x_maxs) - min(x_mins),
    ]

elif get_most:  # request max amount of tissue

    pass

elif groups:  # request zarr around group(s)

    if padding:
        padding *= img_mag  # convert padding from px to μm
    print(f"padding: {padding}")
    window, srange = groupsToVolume(series, groups, padding)

    secs = srange[1] - srange[0]
    start, end_exclude = srange

    print(f"window: {window}")
    print(f"srange: {srange}")

else:  # default to zarr around image center

    center_x, center_y = w // 2, h // 2
    ## TODO: Need to apply section transform to get true center.

    window = [
        (center_x * img_mag) - (w_out / 2),  # x
        (center_y * img_mag) - (h_out / 2),  # y
        w_out,  # w
        h_out,  # h
    ]

print(f"window: {window}")

print("Initializing pyqt...")
app = QApplication(sys.argv)

print("Creating zarr...")
zarr_fp = seriesToZarr(
    series,
    srange,
    img_mag,
    window=window,
    data_fp=output_zarr,
)

# Add labels to zarr if PyReconstruct groups provided
if groups:
    for group in groups:
        print(f"Converting group {group} to labels...")
        seriesToLabels(series, zarr_fp, group)

series.close()

print(f"\nSeries {series.name} exported as zarr")
print("")
print(f"Window:          {[round(elem, 2) for elem in window]}")
print(f"Sections:        {secs} ({start}-{end_exclude - 1})")
print(f"Mag:             {mag}")
print(f"Zarr location:   {zarr_fp}\n")
