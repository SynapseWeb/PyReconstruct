import os
import sys
import numpy as np
import zarr

from PySide6.QtWidgets import QApplication

# add src modules to the system path
sys.path.append(os.path.join(os.getcwd(), "..", ".."))
from PyReconstruct.modules.datatypes import Series
from PyReconstruct.modules.backend.view import SectionLayer

# user-entered info
jser_fp = r"C:\Users\jfalco\Documents\Series\DSNYJ_JSER\DSNYJ.jser"
contour_names = ["d001"]  # use drop-down method with object groups
srange = (100, 151)  # enter manually
window = [16, 15, 10, 10]  # use a stamp (make one of the palette traces a freaking square)
mag = 0.005  # enter manually, but default to section mag

# calculate field attributes
shape = (
    srange[1] - srange[0],
    round(window[3]/mag),
    round(window[2]/mag)
)
pixmap_dim = shape[2], shape[1]  # the w and h of a 2D array

# create the zarr files
data_zg = zarr.open(os.path.join(
    os.path.dirname(jser_fp),
    "data.zarr"
))
raw_zarr = data_zg.zeros("raw", shape=shape, dtype=np.uint8)
labels_zarr = data_zg.zeros(f"labels", shape=shape, dtype=np.uint32)

# open the series
series = Series.openJser(jser_fp)

# open a QApp
app = QApplication([])

# iterate through series
alignment = {}
for snum in range(*srange):
    print(f"Working on section {snum}...")
    section = series.loadSection(snum)
    slayer = SectionLayer(section, series)
    z = snum - srange[0]
    raw_zarr[z] = slayer.generateImageArray(
        pixmap_dim, 
        window
    )
    labels_zarr[z] = slayer.generateLabelsArray(
        pixmap_dim,
        window,
        contour_names
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

labels_zarr.attrs["offset"] = offset
labels_zarr.attrs["resolution"] = resolution

# save additional attributes for loading back into jser
raw_zarr.attrs["window"] = window
raw_zarr.attrs["srange"] = srange
raw_zarr.attrs["true_mag"] = mag
raw_zarr.attrs["alignment"] = alignment

labels_zarr.attrs["window"] = window
labels_zarr.attrs["srange"] = srange
labels_zarr.attrs["true_mag"] = mag
labels_zarr.attrs["alignment"] = alignment

# close the series
series.close()