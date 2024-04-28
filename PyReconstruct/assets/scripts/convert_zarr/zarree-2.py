import os
import sys
os.environ["OPENCV_LOG_LEVEL"] = "FATAL"
os.environ["OPENCV_IO_MAX_IMAGE_PIXELS"] = "18500000000"  # Go big or go home?
import cv2
import zarr
from multiprocessing import Pool
import time

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
    message = "Converting to zarr now..."
else:
    zg = zarr.open(zarr_fp)
    message = "Updating zarr scales now..."

print(message)

def create2D(filename):
    
    print(f"Working on {filename}...", flush=True)
    
    t_start = time.perf_counter()
    
    try:
        # get the image
        if create_new:
            img_fp = os.path.join(img_dir, filename)
            cvim = cv2.imread(img_fp, cv2.IMREAD_GRAYSCALE)
            if cvim is None:
                raise Exception(f"{filename} is not an image file.")
            # write raw image into scale 1
            if filename not in zg["scale_1"]:
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
            if filename not in zg[scale_group]:
                downscaled_cvim = cv2.resize(cvim, (w, h))
                zg[scale_group].create_dataset(filename, data=downscaled_cvim)

    except Exception as e:
        
        print(f"Error with {filename}: ", end="", flush=True)
        print(e, flush=True)

    t_end = time.perf_counter()

    return filename, t_end - t_start

if __name__ == "__main__":

    t_all_start = time.perf_counter()

    with Pool() as p:

        if create_new:
            
            results = p.imap_unordered(create2D, os.listdir(img_dir))
            
        else:
            
            results = p.imap_unordered(create2D, list(zg["scale_1"]))

        for filename, duration in results:

            print(f"Time for conversion {filename}: {round(duration, 2)} s")

    t_all_end = time.perf_counter()

    duration = round(t_all_end - t_all_start, 2)

    print(f"All tasks completed: {duration} s")
