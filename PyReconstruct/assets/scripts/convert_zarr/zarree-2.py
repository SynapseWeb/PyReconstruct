import os
import sys
import time
from multiprocessing import Pool

import cv2
import zarr

os.environ["OPENCV_LOG_LEVEL"] = "FATAL"
os.environ["OPENCV_IO_MAX_IMAGE_PIXELS"] = "18500000000"  # Go big or go home?

IMAGE_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff"}
MIN_DOWNSAMPLED_PIXELS = 1024**2

def clean_windows_path(path):
    
    if not sys.platform.startswith('win'):
        return path
        
    # Remove surrounding quotes if present
    if (path.startswith('"') and path.endswith('"')) or (path.startswith("'") and path.endswith("'")):
        path = path[1:-1]
    
    # Handle paths with nested quotes
    path = path.replace('""', '"').replace("''", "'")
    
    # Replace forward slashes with backslashes for Windows
    path = path.replace('/', '\\')
    
    return path

cores = int(sys.argv[1])  # number of cores to use

if len(sys.argv) == 4:

    img_dir = clean_windows_path(sys.argv[2])
    zarr_fp = sys.argv[3]
    create_new = True
    
elif len(sys.argv) == 3:
    
    zarr_fp = sys.argv[2]
    create_new = False
    
else:

    print("Please provide arguments", flush=True)
    exit()

def image_filenames(img_dir):
    images = []
    skipped = []

    for filename in sorted(os.listdir(img_dir)):
        img_fp = os.path.join(img_dir, filename)
        ext = os.path.splitext(filename)[1].lower()

        if not os.path.isfile(img_fp) or ext not in IMAGE_EXTENSIONS:
            skipped.append(filename)
            continue

        images.append(filename)

    if skipped:
        print(
            "Skipping non-image entries: " + ", ".join(skipped),
            flush=True
        )

    if not images:
        raise Exception(f"No image files found in {img_dir}.")

    return images


def scale_names_for_shape(shape):
    h, w = shape
    exp = 0
    scale_names = ["scale_1"]

    while h * w >= MIN_DOWNSAMPLED_PIXELS:
        h = round(h / 2)
        w = round(w / 2)
        exp += 1
        scale_names.append(f"scale_{2**exp}")

    return scale_names


def ensure_scale_groups(zg, images):
    if create_new:
        img_fp = os.path.join(img_dir, images[0])
        cvim = cv2.imread(img_fp, cv2.IMREAD_GRAYSCALE)
        if cvim is None:
            raise Exception(f"{images[0]} is not an image file.")
        scale_names = scale_names_for_shape(cvim.shape)
    else:
        first_image = images[0]
        scale_names = scale_names_for_shape(zg["scale_1"][first_image].shape)

    for scale_group in scale_names:
        if scale_group not in zg:
            zg.create_group(scale_group)


def validate_zarr(zg, images):
    missing = []

    for filename in images:
        if filename not in zg["scale_1"]:
            missing.append(f"scale_1/{filename}")
            continue

        for scale_group in scale_names_for_shape(zg["scale_1"][filename].shape)[1:]:
            if scale_group not in zg or filename not in zg[scale_group]:
                missing.append(f"{scale_group}/{filename}")

    if missing:
        preview = "\n".join(missing[:20])
        remaining = len(missing) - 20
        if remaining > 0:
            preview += f"\n... and {remaining} more"
        raise Exception(f"Zarr conversion incomplete:\n{preview}")


def create2D(args):
    zg, filename = args
    
    print(f"Working on {filename}...", flush=True)
    
    t_start = time.perf_counter()
    
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
    while h * w >= MIN_DOWNSAMPLED_PIXELS:
        h = round(h/2)
        w = round(w/2)
        exp += 1
        scale_group = f"scale_{2**exp}"
        if scale_group not in zg:
            zg.create_group(scale_group)
        if filename not in zg[scale_group]:
            downscaled_cvim = cv2.resize(cvim, (w, h))
            zg[scale_group].create_dataset(filename, data=downscaled_cvim)

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

    if create_new:
        images = image_filenames(img_dir)
    else:
        images = sorted(list(zg["scale_1"]))
        if not images:
            raise Exception(f"No scale_1 images found in {zarr_fp}.")

    ensure_scale_groups(zg, images)

    while True and processes > 0:

        try:
            
            print(f"\n\nAttempting to convert with n cores: {processes}\n\n")

            t_all_start = time.perf_counter()

            with Pool(processes) as p:

                args = zip([zg] * len(images), images)
                    
                results = p.imap_unordered(create2D, args)

                for filename, duration in results:

                    print(f"Time for conversion {filename}: {round(duration, 2)} s")

            t_all_end = time.perf_counter()

            duration = round(t_all_end - t_all_start, 2)

            print(f"All tasks completed: {duration} s")

            validate_zarr(zg, images)
            print("Zarr validation complete.")

            break
        
        except Exception as e:

            print(f"Failed with core n of {processes} with exception: {e}")
            processes -= 1

    if processes == 0:
        raise SystemExit(1)
