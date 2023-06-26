import os
import sys
os.environ["OPENCV-LOG-LEVEL"] = "FATAL"
import cv2
import zarr
from multiprocessing import Pool

if len(sys.argv) == 3:
    
    img_dir = sys.argv[1]
    zarr_fp = sys.argv[2]
    create_new = True
    
elif len(sys.argv) == 2:
    
    zarr_fp = sys.argv[1]
    create_new = False
    
else:

    print("Please provide arguments", flush=True)
    exit()

if create_new:
    zg = zarr.group(zarr_fp, overwrite=True)
    zg.create_group("scale_1")
else:
    zg = zarr.open(zarr_fp)

def create2D(filename):
    print(f"Working on {filename}...", flush=True)
    try:
        # get the image
        if create_new:
            img_fp = os.path.join(img_dir, filename)
            cvim = cv2.imread(img_fp, cv2.IMREAD_GRAYSCALE)
            if cvim is None:
                raise Exception(f"{filename} is not an image file.")
            # write raw image into scale 1
            zg["scale_1"].create_dataset(filename, data=cvim)
        else:
            cvim = zg["scale_1"][filename][:]

        # keep downsampling image by 2 until size is below 1024x1024 pixels
        h, w = cvim.shape
        exp = 0
        while h * w >= 1024**2:
            h = round(h/2)
            w = round(w/2)
            exp += 1
            scale_group = f"scale_{2**exp}"
            if scale_group not in zg:
                zg.create_group(scale_group)
            downscaled_cvim = cv2.resize(cvim, (h, w))
            zg[scale_group].create_dataset(filename, data=downscaled_cvim)

    except Exception as e:
        print(f"Error with {filename}: ", end="", flush=True)
        print(e, flush=True)

if __name__ == "__main__":

    with Pool(1) as p:

        if create_new:
            
            p.map(create2D, os.listdir(img_dir))
            
        else:
            
            p.map(create2D, list(zg["scale_1"]))
