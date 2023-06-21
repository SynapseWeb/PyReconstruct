import os
import sys
import cv2
import zarr
from multiprocessing import Pool

scales = [1, 4, 16]

img_dir = sys.argv[1]
zarr_fp = sys.argv[2]

zg = zarr.group(zarr_fp, overwrite=True)
for s in scales:
    zg.create_group(f"scale_{s}")

def create2D(filename):
    print(f"Working on {filename}...")
    try:
        img_fp = os.path.join(img_dir, filename)
        cvim = cv2.imread(img_fp, cv2.IMREAD_GRAYSCALE)
        if not cvim:
            raise Exception(f"{filename} is not an image file.")
        h, w = cvim.shape
        for s in scales:
            if s != 1:
                downscaled_cvim = cv2.resize(cvim, (round(h/s), round(w/s)))
            else:
                downscaled_cvim = cvim
            zg[f"scale_{s}"].create_dataset(filename, data=downscaled_cvim)

    except Exception as e:
        print(f"Error with {filename}: ", end="")
        print(e)

if __name__ == "__main__":
    with Pool(1) as p:
        p.map(create2D, os.listdir(img_dir))

    print("Finished successfully!")