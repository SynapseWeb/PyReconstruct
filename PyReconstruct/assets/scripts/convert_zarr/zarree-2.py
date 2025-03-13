import os
import sys
import time
from multiprocessing import Pool

import cv2
import zarr

os.environ["OPENCV_LOG_LEVEL"] = "FATAL"
os.environ["OPENCV_IO_MAX_IMAGE_PIXELS"] = "18500000000"  # Go big or go home?

cores = int(sys.argv[1])  # number of cores to use

if len(sys.argv) == 4:
    
    img_dir = sys.argv[2]
    zarr_fp = sys.argv[3]
    create_new = True
    
elif len(sys.argv) == 3:
    
    zarr_fp = sys.argv[2]
    create_new = False
    
else:

    print("Please provide arguments", flush=True)
    exit()

def create2D(args):
    zg, filename = args
    
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

    if create_new:
        
        zg = zarr.group(zarr_fp, overwrite=True)
        zg.create_group("scale_1")
        message = "Converting to zarr now..."
        
    else:
        
        zg = zarr.open(zarr_fp)
        message = "Updating zarr scales now..."

    print(message)

    processes = cores

    while True:

        try:
            
            print(f"\n\nAttempting to convert with n cores: {processes}\n\n")

            t_all_start = time.perf_counter()

            with Pool(processes) as p:

                if create_new:

                    images = os.listdir(img_dir)
                                        
                else:

                    images = list(zg["scale_1"])

                args = zip([zg] * len(images), images)
                    
                results = p.imap_unordered(create2D, args)

                for filename, duration in results:

                    print(f"Time for conversion {filename}: {round(duration, 2)} s")

            t_all_end = time.perf_counter()

            duration = round(t_all_end - t_all_start, 2)

            print(f"All tasks completed: {duration} s")

            break
        
        except:

            processes -= 1
            print(f"\n\nAttempting to convert with n cores: {processes}\n\n")
