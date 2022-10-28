import os

import cv2
import cv2
import zarr

os.chdir(input("Enter the images directory: "))

zarr_name = input("What would you like to name your zarr file?: ")
if not zarr_name.endswith(".zarr"):
    zarr_name = zarr_name + ".zarr"

for fname in os.listdir("."):
    if fname.endswith(".tif"):
        print(f"Working on {fname}...")
        cvim = cv2.imread(fname, cv2.IMREAD_GRAYSCALE)
        zarr.save(os.path.join(zarr_name, fname), cvim)

