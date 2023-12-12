"""Create neuroglancer-formatted zarrs from PyReconstruct jser files."""

# Requires image-get-center (see below) if using with non-zarr images

import sys
import os
from pathlib import Path
import zarr
import subprocess
import argparse
import tomllib

from PySide6.QtWidgets import QApplication

# Imports are a nightmare (set repo root here)
project_dir = Path(__file__).parents[1]
sys.path.append(str(project_dir))

from PyReconstruct.modules.datatypes import Series
from PyReconstruct.modules.backend.autoseg import seriesToZarr, seriesToLabels


parser = argparse.ArgumentParser(prog="create_ng_zarr", description=__doc__)

# poitional args
parser.add_argument('jser', type=str, nargs='?', help="Filepath of a valid jser file.")

# optional args
parser.add_argument('--config', type=str, help="filepath to a toml config file")
parser.add_argument("--height", "-y", type=float, default=2.0, help='height in μm (default %(default)s μm)')
parser.add_argument("--width", "-x", type=float, default=2.0, help='width in μm (default %(default)s μm)')
parser.add_argument("--sections", "-s", type=int, default=50, help='number of sections to include (default %(default)s sections)')
parser.add_argument("--mag", "-m", type=float, default=0.008, help='output zarr mag in μm/vox (default %(default)s μm/vox)')
parser.add_argument("--groups", "-g", type=str, action='append', nargs="*", default=None, help='PyReconstruct object groups to include as labels (default %(default)s μm/vox)')

args = parser.parse_args()

# Change defaults according to optional toml config file
if args.config:
    with open(args.config, 'rb') as fp:
        try:            
            parser.set_defaults(**tomllib.load(fp))
        except tomllib.TOMLDecodeError:
            parser.error("Malformed toml config file.")
    if args.groups: parser.set_defaults(groups=None)  # override toml acting as defaults if --groups called
    args = parser.parse_args()

# Ensure "valid" jser provided
if not args.jser or not os.path.exists(args.jser):
    parser.error("Please provide filepath to a valid jser.")

jser_fp  = args.jser
h_out    = float(args.height)
w_out    = float(args.width)
secs     = int(args.sections)
mag      = float(args.mag)

def flatten_list(nested_list):
    """Recursively flatten lists to handle groups."""
 
    if not(bool(nested_list)):  # empty list?
        return nested_list
 
    if isinstance(nested_list[0], list):
 
        return flatten_list(*nested_list[:1]) + flatten_list(nested_list[1:])
 
    return nested_list[:1] + flatten_list(nested_list[1:])

groups = flatten_list(args.groups) if args.groups else None

print("Opening series...")
series = Series.openJser(jser_fp)

print("Gathering args...")
sections = sorted(list(series.sections.keys()))

mid = len(sections) // 2
start = mid - (secs // 2) - 1
end_exclude = mid + (secs // 2) - 1

srange = (sections[start], sections[end_exclude])

# sample a section to get the true magnification
section = series.loadSection(sections[0])

if series.src_dir.endswith("zarr"):
    
    scale_1 = os.path.join(series.src_dir, "scale_1")
    one_img = os.path.join(scale_1, os.listdir(scale_1)[10])  # stear clear of cal grid

    z = zarr.open(one_img, "r")
    h, w = z.shape
    
    center_x_px, center_y_px = w // 2, h // 2

    ## TODO: Do the above center values take into account transformations?
    
else:
    
    cmd = f"~/tmp/image-get-center {series.src_dir}"
    center = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    center_x_px, center_y_px = map(float, center.stdout.strip().split(" "))

    ## TODO: Need to apply section transform to get true center.
    ## The above will work for now.

window = [
    (center_x_px * section.mag) - (w_out / 2),  # x
    (center_y_px * section.mag) - (h_out / 2),  # y
    w_out, # w
    h_out # h
]

print("Initializing pyqt...")
app = QApplication(sys.argv)

print("Creating zarr...")
zarr_fp = seriesToZarr(
    series,
    srange,
    mag,
    window=window,
#    output_dir=output_dir
)

# Add labels to zarr if PyReconstruct groups provided
if groups:
    for group in groups:
        print(f'Coverting group {group} to labels...') 
        seriesToLabels(series, zarr_fp, group)

series.close()

print(f"\nSeries {series.name} exported as zarr")
print("")
print(f"Window:          {[round(elem, 2) for elem in window]}")
print(f"Sections:        {secs} ({start}-{end_exclude - 1})")
print(f"Mag:             {mag}")
print(f"Zarr location:   {zarr_fp}\n")
