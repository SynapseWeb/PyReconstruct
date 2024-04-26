"""Export section traces as svg."""

import os
import cv2
import zarr
from PyReconstruct.modules.datatypes.series import Series
from PyReconstruct.modules.constants import (svg_blank, path_blank)


def get_img_dim(series, section):

    if series.src_dir.endswith(".zarr"):  ## TODO: Need to validate zarrs more appropriately

        img_scale_1 = os.path.join(series.src_dir, "scale_1", section.src)
        h, w = zarr.open(img_scale_1).shape

    else:

        img_fp = os.path.join(series.src_dir, section.src)
        h, w, _ = cv2.imread(img_fp).shape

    return h, w


def points_to_svg_str(points, mag, img_height, path_name):
    """Convert points to a string for svg."""
    
    output = []
    
    for i, point in enumerate(points):

        x = str(round(point[0] / mag))
        y = str(round( img_height - (point[1] / mag) )) # flip y!

        if i != 0:
            
            output.append(f"{x},{y}")

    output = " ".join(output)

    path = path_blank.replace("[COORDINATES]", output)
    path = path.replace("[NAME]", path_name)
    path = path.replace("[WIDTH]", "1")
    path = path.replace("[COLOR]", "#000000")
            
    return path


def exportTraces(series: Series):

    section = series.loadSection(series.current_section)
    mag = section.mag
    contours = section.contours

    img_height, img_width = get_img_dim(series, section)

    paths = []
    
    for obj, data in contours.items():
        
        for i, trace in enumerate(data.getTraces()):

            path_name = f"{obj}-{i}"
            path = points_to_svg_str(trace.points, mag, img_height, path_name)

            paths.append(path)

    paths_str = "\n".join(paths)

    svg_output = svg_blank.replace("[WIDTH]", str(img_width))
    svg_output = svg_output.replace("[HEIGHT]", str(img_height))
    svg_output = svg_output.replace("[PATHS]", paths_str)

    print(svg_output)
