import os
import sys
import cv2
import zarr
from multiprocessing import Pool

img_dir = sys.argv[1]
zarr_fp = sys.argv[2]

def create2D(filename):
    print(f"Working on {filename}...")
    try:
        img_fp = os.path.join(img_dir, filename)
        cvim = cv2.imread(img_fp, cv2.IMREAD_GRAYSCALE)
        zarr.save(os.path.join(zarr_fp, filename), cvim)
    except Exception as e:
        print(f"Error with {filename}: ", end="")
        print(e)
    print(f"Finished with {filename}")

if __name__ == "__main__":
    with Pool(1) as p:
        p.map(create2D, os.listdir(img_dir))

    print("Finished successfully!")