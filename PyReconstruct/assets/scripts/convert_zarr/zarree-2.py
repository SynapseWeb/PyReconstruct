import os
import sys
import time
import shutil
from multiprocessing import Pool, freeze_support

import cv2
import zarr

os.environ["OPENCV_LOG_LEVEL"] = "FATAL"
os.environ["OPENCV_IO_MAX_IMAGE_PIXELS"] = "18500000000"  # Go big or go home?

IMAGE_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff"}
MIN_DOWNSAMPLED_PIXELS = 1024**2

# Cap concurrency: each worker holds a full-resolution tile in memory, and a
# large worker count multiplies filesystem/metadata pressure for little gain
# (the work is I/O bound). Bounded well below typical core counts on purpose.
MAX_WORKERS = 8

# Require a little more free space than estimated before starting.
DISK_SAFETY_FACTOR = 1.15

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
    zarr_fp = clean_windows_path(sys.argv[3])
    create_new = True

elif len(sys.argv) == 3:

    zarr_fp = clean_windows_path(sys.argv[2])
    create_new = False

else:

    print("Please provide arguments", flush=True)
    exit()


def open_zarr_with_retry(fp, mode=None, attempts=5, delay=0.2):
    """Open a zarr store, retrying briefly on transient filesystem errors.

    Network/synced drives (e.g. OneDrive) can momentarily fail to serve a
    freshly written metadata file; a short backoff absorbs those hiccups
    instead of crashing.
    """
    last_err = None
    for attempt in range(attempts):
        try:
            return zarr.open(fp) if mode is None else zarr.open(fp, mode=mode)
        except (KeyError, OSError, zarr.errors.GroupNotFoundError) as e:
            last_err = e
            time.sleep(delay * (attempt + 1))
    raise last_err


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


def _dir_size(path):
    """Total size of all files under path (metadata-only walk)."""
    total = 0
    for root, _dirs, files in os.walk(path):
        for name in files:
            try:
                total += os.path.getsize(os.path.join(root, name))
            except OSError:
                pass
    return total


def estimate_required_bytes(images):
    """Rough estimate of the additional disk space the scales will need.

    Each halving stores 1/4 the pixels, so the downsampled levels sum to
    ~1/3 of scale_1 (1/4 + 1/16 + ...). For an existing zarr we measure
    scale_1's on-disk (compressed) size; for a new zarr we approximate
    scale_1 from the source image file sizes.
    """
    if create_new:
        src_total = 0
        for filename in images:
            try:
                src_total += os.path.getsize(os.path.join(img_dir, filename))
            except OSError:
                pass
        # new scale_1 (~ source size) plus downscales (~1/3 of scale_1)
        return int(src_total * (1 + 1 / 3))

    scale1_size = _dir_size(os.path.join(zarr_fp, "scale_1"))
    # only the downscales are new (~1/3 of scale_1)
    return int(scale1_size / 3)


def check_disk_space(images):
    """Abort up front if the target volume can't hold the new scales."""
    required = int(estimate_required_bytes(images) * DISK_SAFETY_FACTOR)
    target = os.path.dirname(os.path.abspath(zarr_fp)) or "."
    free = shutil.disk_usage(target).free
    gb = 1024 ** 3

    print(
        f"Estimated additional space needed: ~{required / gb:.2f} GB; "
        f"free on target volume: {free / gb:.2f} GB",
        flush=True,
    )

    if free < required:
        raise SystemExit(
            "Not enough free disk space to generate scaled images.\n"
            f"  Estimated need (with margin): ~{required / gb:.2f} GB\n"
            f"  Available on target volume:   {free / gb:.2f} GB\n"
            "Free up space or choose an output location with more room, "
            "then try again."
        )


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
    """Worker: read one image and return its resized levels.

    Workers never write to the zarr store -- they only read/compute and hand
    the arrays back to the main process, which is the sole writer. This keeps
    the conversion free of cross-process write races and makes a failure
    (e.g. a full disk) surface once, in the main process.
    """
    filename, create_new, img_dir, zarr_fp = args

    print(f"Working on {filename}...", flush=True)

    t_start = time.perf_counter()

    scales = {}

    if create_new:
        img_fp = os.path.join(img_dir, filename)
        cvim = cv2.imread(img_fp, cv2.IMREAD_GRAYSCALE)
        if cvim is None:
            raise Exception(f"{filename} is not an image file.")
        # full-resolution level is written by the main process too
        scales["scale_1"] = cvim
    else:
        # read-only handle: concurrent reads are safe and need no disk space
        src = open_zarr_with_retry(zarr_fp, mode="r")
        cvim = src["scale_1"][filename][:]

    # keep downsampling by 2 until below MIN_DOWNSAMPLED_PIXELS
    h, w = cvim.shape
    exp = 0
    while h * w >= MIN_DOWNSAMPLED_PIXELS:
        h = round(h / 2)
        w = round(w / 2)
        exp += 1
        scales[f"scale_{2**exp}"] = cv2.resize(cvim, (w, h))

    return filename, scales, time.perf_counter() - t_start


if __name__ == "__main__":

    freeze_support()

    if create_new:

        zg = zarr.group(zarr_fp, overwrite=True)
        zg.create_group("scale_1")
        message = "Converting to zarr now..."

    else:

        zg = open_zarr_with_retry(zarr_fp, mode="a")
        message = "Updating zarr scales now..."

    print(message, flush=True)

    if create_new:
        images = image_filenames(img_dir)
    else:
        images = sorted(list(zg["scale_1"]))
        if not images:
            raise Exception(f"No scale_1 images found in {zarr_fp}.")

    # fail fast if the target volume cannot hold the new scales
    check_disk_space(images)

    # pre-create every scale group up front so workers never create groups
    ensure_scale_groups(zg, images)

    processes = max(1, min(cores, MAX_WORKERS))
    print(f"Converting with {processes} worker process(es)...", flush=True)

    t_all_start = time.perf_counter()

    # plain, picklable args only -- never the zarr group itself
    args = [
        (filename, create_new, img_dir if create_new else None, zarr_fp)
        for filename in images
    ]

    with Pool(processes) as p:

        # imap (ordered) + main-as-sole-writer => deterministic, race-free writes
        for filename, scales, duration in p.imap(create2D, args):

            for scale_group, arr in scales.items():
                if filename not in zg[scale_group]:
                    zg[scale_group].create_dataset(filename, data=arr)

            print(f"Time for conversion {filename}: {round(duration, 2)} s", flush=True)

    print(f"All tasks completed: {round(time.perf_counter() - t_all_start, 2)} s", flush=True)

    validate_zarr(zg, images)
    print("Zarr validation complete.", flush=True)
