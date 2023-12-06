"""Create neuroglancer-formatted zarrs from PyReconstruct jser files."""

# Requires image-get-center (see below) if using with non-zarr images

import sys
import os
from pathlib import Path
import zarr
import subprocess
import argparse
import tomllib
import itertools

from PySide6.QtWidgets import QApplication

# Imports are a nightmare (set repo root here)
project_dir = Path(__file__).parents[1]
sys.path.append(str(project_dir))

from PyReconstruct.modules.datatypes import Series
from PyReconstruct.modules.backend.autoseg import seriesToZarr
from PyReconstruct.modules.backend.autoseg import seriesToLabels


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
        parser.set_defaults(**tomllib.load(fp))
    args = parser.parse_args()

# Ensure "valid" jser provided
if not args.jser or not os.path.exists(args.jser):
    parser.error("Please provide filepath to a valid jser.")

jser_fp = args.jser
h_out = float(args.height)
w_out = float(args.width)
secs = int(args.sections)
mag = float(args.mag)
groups = list(itertools.chain(*args.groups)) if args.groups else None

print(jser_fp, h_out, w_out, secs, mag, groups)


#sys.exit("bye-bye times")


print("Opening series...")
series = Series.openJser(jser_fp)

print("Gathering args...")
sections = sorted(list(series.sections.keys()))

mid = len(sections) // 2
start = mid - (secs // 2) - 1
end_exclude = mid + (secs // 2) - 1

srange = (sections[start], sections[end_exclude])

if series.src_dir.endswith("zarr"):
    
    scale_1 = os.path.join(series.src_dir, "scale_1")
    one_img = os.path.join(scale_1, os.listdir(scale_1)[10])  # stear clear of cal grid

    z = zarr.open(one_img, "r")
    h, w = z.shape
    
    center_x, center_y = w // 2, h // 2
    
else:
    
    cmd = f"~/tmp/image-get-center {series.src_dir}"
    center = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    center_x, center_y = map(float, center.stdout.strip().split(" "))

# sample a section to get the true magnification
section = series.loadSection(sections[0])

window = [
    (center_x * section.mag) - (w_out / 2),  # x
    (center_y * section.mag) - (h_out / 2),  # y
    w_out,  # w
    h_out  # h
]

print("Initializing pyqt...")
app = QApplication(sys.argv)

print("Creating zarr...")
zarr_fp = seriesToZarr(
    series,
    f"{series.name}",
    srange,
    mag,
    output_dir="",
    window=window
)

series.close()

print(f"\nSeries {series.name} exported as zarr")
print(f"Window: {window}")
print(f"Total sections {secs} ({start} through {end_exclude - 1})")
print(f"Output path: {zarr_fp}\n")
