import os
import sys
import zarr
import numpy as np

# add src modules to the system path
sys.path.append(os.path.join(os.getcwd(), "..", ".."))
from PyReconstruct.modules.datatypes import Series

def cropZarr(series_fp : str, obj_name : str, radius : float):
    """Crop the zarr file for a series.
    
        Params:
            series_fp (str): the filepath for the series jser
            obj_name (str): the name of the object to crop around
            radius (float): the radius of the crop
    """
    # open the series and check that it uses a zarr file
    series = Series.openJser(series_fp)
    if not series.src_dir.endswith(".zarr"):
        raise Exception("This series does not use a zarr file for its images.")
    
    # set up the new zarr folder
    zarr_name = os.path.basename(series.src_dir)[:-5]
    new_zarr_fp = os.path.join(
        os.path.dirname(series.src_dir),
        f"{zarr_name}_{obj_name}_crop.zarr"
    )

    # iterste through the sections
    for snum, section in series.enumerateSections(
        message="Cropping images..."
    ):
        # get the zarr image
        image = zarr.open(os.path.join(
            series.src_dir, section.src
        ))
        cropped = zarr.zeros(image.shape, dtype=np.uint8)

        # check if object exists on the section (image will be blank otherwise)
        if obj_name in section.contours:
            # get the crop boundaries
            xmin, ymin, xmax, ymax = section.contours[obj_name].getBounds()
            l = round((xmin - radius) / section.mag)
            if l < 0:
                l = 0
            r = round((xmax + radius) / section.mag)
            if r > image.shape[1]:
                r = image.shape[1]
            b = round(image.shape[0] - ((ymin - radius) / section.mag))
            if b > image.shape[0]:
                b = image.shape[0]
            t = round(image.shape[0] - ((ymax + radius) / section.mag))
            if t < 0:
                t = 0

            # crop the image
            cropped[t:b, l:r] = image[t:b, l:r]
        
        zarr.save(
            os.path.join(
                new_zarr_fp, 
                section.src
            ),
            cropped
        )
    
    series.close()

jser_fp = input("Jser filepath: ")
obj_name = input("Object name to crop around: ")
radius = float(input("Radius around BOUNDARY of object to include: "))

cropZarr(jser_fp, obj_name, radius)