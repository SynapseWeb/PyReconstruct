"""
How to use this program:

This program will take a jser series and convert it into a zarr file
that can be viewed in Neuroglancer.

If you have not run this program on your series before, the jser file
MUST be in the same folder as the series images.

If you have an existing zarr file created previously by this
program and you wish to add another set of labels to it, the zarr
file and jser file MUST be in the same folder.

You will most likely need to pip install the following:
pip install opencv-python
pip install numpy
pip install zarr
pip install scikit-image

When running the program it will ask for:
1. The file path for the jser file
    - Find the file path and copy/paste it into the command line

2. The file path for the object names file
    - This file will contains the names of the objects you wish to import to zarr
    - In this file, write the name of each object on its own line
    - Ex:
        d01
        d02
        d02c05
        axon1
    - This file can be in any format (.txt, .csv, etc.)

3. The label name for the labels subfolder
    - This is a user-defined name
    - The subfolder in the zarr file will be named:
        labels_[the name you entered]
    - Be sure not to choose a label name that already exists
"""

import os
import sys
import cv2
import math
import numpy as np
import zarr
import shutil
from skimage.draw import polygon

# add src modules to the system path
sys.path.append(os.path.join(os.getcwd(), "..", ".."))
from PyReconstruct.modules.datatypes import Series

# IMAGE FUNCTIONS

def transformImage(image_location : str, tform_coefs : list, zarr_group : zarr.hierarchy.Group):
    """Transform an image (ignores translation).

    The returned image is the transformed image with adjusted borders so that no part of the image is cut off.
    
        Params:
            image_location (str): the image to transform
            tform_coefs (list): the six transform coefficients
        Returns:
            (np.ndarray) the transformed image
            (origin) the coordinates for the bottom left corner
    """
    # load the image
    if ".zarr" in image_location:
        image = np.array(zarr.open(image_location))
    else:
        image = cv2.imread(image_location, cv2.IMREAD_GRAYSCALE)

    # create the affine transformation matrix
    tform = tform_coefs.copy()
    tform[5], tform[2] = 0, 0
    tform[1] *= -1
    tform[3] *= -1
    tform += [0, 0, 1]
    tform = np.array(tform, dtype="f8").reshape(3, 3)

    # get the corners of the image and tformed image
    height, width = image.shape[:2]
    corners = np.array([[0, width, width, 0], [0, 0, height, height], [1, 1, 1, 1]])
    tformed_corners = np.matmul(tform, corners)

    # get minimum and maximum values for the transformation
    xmin = tformed_corners[0,:].min()
    if xmin < 0:
        offset_x = -xmin
    else:
        xmin, offset_x = 0, 0
    ymin = tformed_corners[1,:].min()
    if ymin < 0:
        offset_y = -ymin
    else:
        ymin, offset_y = 0, 0
    xmax = tformed_corners[0,:].max()
    ymax = tformed_corners[1,:].max()

    # calculate dimensions
    tformed_width = math.ceil(xmax - xmin)
    tformed_height = math.ceil(ymax - ymin)

    # offset is the translation required to keep the entire picture in the image
    offset_x = -xmin if xmin < 0 else 0
    offset_y = -ymin if ymin < 0 else 0
    adjusted_tform = tform.copy()
    adjusted_tform[0, 2] += offset_x
    adjusted_tform[1, 2] += offset_y

    # transform the image and calculate bottom left corner (origin)
    tformed_image = cv2.warpAffine(image, adjusted_tform[0:2,:], (tformed_width, tformed_height))
    origin = (round(tformed_corners[0, 3] - tform[0, 2] + offset_x), round(tformed_corners[1, 3] - tform[1, 2] + offset_y))

    # write data to zarr group
    if "im_fps" in zarr_group.attrs:
        zarr_group.attrs["im_fps"].append(image_location)
    else:
        zarr_group.attrs["im_fps"] = [image_location]
    z = zarr_group.array(image_location, tformed_image)
    z.attrs["origin"] = origin
    z.attrs["shape"] = tformed_image.shape

def calculateField(images_data : tuple) -> tuple:
    """Get the shape and origin of the field.
    
        Params:
            images (tuple): list of following data
                - tform_coefs: the transforms as a list of six numbers
                - image: the transformed image
                - origin: the location of the bottom left corner of the image
        Returns:
            (tuple) the dimensions of the field
            (tuple) the origin of the field
    """
    # store the min and max x and y values
    min_x = None
    max_x = None
    min_y = None
    max_y = None

    for tform_coefs, shape, origin, in images_data:
        # get tform offset and image dimensions
        offset = (tform_coefs[2], tform_coefs[5])
        height, width = shape
        l = offset[0] - origin[0]
        r = offset[0] - origin[0] + width
        b = offset[1] - (height - origin[1])
        t = offset[1] - (height - origin[1]) + height

        # check
        if min_x is None or l < min_x:
            min_x = math.floor(l)
        if max_x is None or r > max_x:
            max_x = math.ceil(r)
        if min_y is None or b < min_y:
            min_y = math.floor(b)
        if max_y is None or t > max_y:
            max_y = math.ceil(t)
    
    h = max_y - min_y
    w = max_x - min_x
    origin = (-min_x, max_y)
    return (h, w), origin

def placeImageInField(field, field_index : int, field_origin : tuple, im, im_origin : tuple, offset : tuple):
    """Places an image within a black background.
    
        Params:
            field: the array for the entire field in 3D
            field_index (int) the section number
            shape (tuple): dimensions of full black backdrop (aka the field)
            field_origin (tuple): the coordinates for the field origin
            im: the array for the image to be placed in the field
            offset (tuple): translation compenent of the transformation
        Returns:
            (np.ndarray) the image placed within the field
    """
    # get coordinates for where to place the image
    x = round(field_origin[0] - im_origin[0] + offset[0])
    y = round(field_origin[1] - im_origin[1] - offset[1])
    h, w = im.shape[:2]

    # place image in field using a slice
    field[field_index, y : y+h, x : x+w] = im

def jsonImagesToZarr(series_fp : str):
    print("\nLoading series image data...")

    # open the jser file
    series = Series.openJser(series_fp)

    # acquire list of image locations and transforms
    if series.src_dir.endswith(".zarr"):  # check for zarr images
        zarr_src = True
    else:
        zarr_src = False
    image_locations = []
    tforms = []
    for snum, section in series.enumerateSections(
        message="Gathering section data..."
    ):
        if zarr_src:
            image_locations.append(
                os.path.join(
                    os.path.basename(series.src_dir),
                    os.path.basename(section.src)
                )
            )
        else:
            image_locations.append(os.path.basename(section.src))
        tform = section.tforms["default"].getList()
        mag = section.mag
        tform[2] /= mag
        tform[5] /= mag
        tforms.append(tform)

    # create the zarr group
    data_zg = zarr.open("data.zarr")
    images_zg = data_zg.create_group("images_temp")

    # transform each image
    counter = 1
    for image_location, tform in zip(image_locations, tforms):
        print(f"Transforming images... | {counter/len(tforms)*100:.1f}%", end="\r")
        transformImage(image_location, tform, images_zg)
        counter += 1
    print()

    # gather data from zarr attributes
    images_data = []
    for image_location, tform in zip(image_locations, tforms):
        im_zarr = images_zg[image_location]
        shape = im_zarr.attrs["shape"]
        origin = im_zarr.attrs["origin"]
        images_data.append((tform, shape, origin))

    # get the field for the images
    print("Calculating field size...")
    field_shape, field_origin = calculateField(images_data)

    # create field image zarr group
    field_3D_shape = ((len(series.sections),) + field_shape)
    field_zarr = data_zg.zeros("raw", shape=field_3D_shape, dtype="uint8")

    # place each image in its field
    i = 0
    for im_loc, tform in zip(image_locations, tforms):
        print(f"Placing images in field... | {(i+1)/len(tforms)*100:.1f}%", end="\r")
        im_zarr = images_zg[im_loc]
        im_origin = im_zarr.attrs["origin"]
        offset = (tform[2], tform[5])
        placeImageInField(field_zarr, i, field_origin, im_zarr, im_origin, offset)

        # delete the tformed image data
        im_zarr.resize(0, 0)
        i += 1
    print()

    # delete the image temp folder
    shutil.rmtree("data.zarr/images_temp")
    
    print("Saving zarr atrributes...")

    # get values for saving zarr files (from last known section)
    xy_res = int(section.mag * 1000)
    z_res = int(section.thickness * 1000)
    resolution = [z_res, xy_res, xy_res]
    offset = [0, 0, 0]

    # save attributes
    field_zarr.attrs["offset"] = offset
    field_zarr.attrs["resolution"] = resolution
    field_zarr.attrs["field_origin"] = field_origin

    # close the series
    series.close()


# CONTOUR FUNCTIONS


def transformContour(contour : list, tform : list) -> list:
    """Apply a transform to a set of points.
    
        Params:
            contour (list): a list of points
            tform (list): six affine transform coefs
        Returns:
            (list) the list of transformed points
    """
    # create the tform matrix
    tform = tform.copy()
    tform += [0, 0, 1]
    tform = np.array(tform, dtype="f8").reshape(3, 3)

    # transform each point
    tformed_contour = []
    for p in contour:
        tformed_p = np.matmul(tform, [[p[0]], [p[1]], [1]])
        tformed_contour.append((tformed_p[0,0], tformed_p[1,0]))
    return tformed_contour

def convertToPixelCoords(contour : list, tform : list, mag : float, field_shape : tuple, field_origin : tuple) -> list:
    """Transforms and converts a contour in field coordinates into pixel coordinates.
    
        Params:
            contour (list): the list of field points
            tform (list): the six coefficients for the affin transform
            mag (float): pixels/micron for the section
            field_shape (tuple): the shape of the 2D field
            field_origin (tuple): the origin of the 2D field
        Returns:
            (list): the contour in pixels
    """
    # transform the contour
    tformed = transformContour(contour, tform)

    # convert the contour into pixel coords
    height = field_shape[0]
    pix_contour = []
    for p in tformed:
        pix_x = round(p[0] / mag) + field_origin[0]
        pix_y = (height - round(p[1] / mag)) - (height - field_origin[1])
        pix_contour.append((pix_x, pix_y))
    return pix_contour

def generateIDs(trace_names : list, start=100, increment=50) -> dict:
    """Generates a set of IDs for each object name.
    
        Params:
            trace_names (list): the list of names
            start (int): the first id num
            increment (int): the value to increment each id by
        Returns:
            (dict) the ids that correspond to each name
    """
    counter = start
    name_ids = {}
    for name in trace_names:
        name_ids[name] = counter
        counter += increment
    return name_ids

def drawContoursinField(all_contours : dict, tform : list, mag : float, contours_zarr, index : int, field_origin : tuple):
    """Draw a set of contours in a 2D field.
    
        Params:
            all_contours (dict): contains all contours to draw (id : list of contours)
            tform (list): the 6 affine transform coefs
            mag (float): pixels/micron for the section
            contours_zarr: the 3D array containing the contour points
            index (int): the section number
            field_origin (tuple): the origin of the 2D field
    """
    field_shape = contours_zarr[index].shape

    # draw the filled-in contours
    for id, contours in all_contours.items():
        for contour in contours:
            # convert contour and create numpy array
            pix_contour = convertToPixelCoords(contour, tform, mag, field_shape, field_origin)
            pix_contour = np.array(pix_contour)

            # get polygon coords
            r = pix_contour[:,1]
            c = pix_contour[:,0]
            rr, cc = polygon(r , c)

            # fill in polygon coords
            try:
                contours_zarr[index, rr, cc] = id
            except IndexError:
                print("index error found") # occurs if there is a trace outside the field
                continue

def jsonContoursToZarr(series_fp, trace_names, label_name, zarr_file):
    print("\nLoading series contour data...")

    # open the jser series
    series = Series.openJser(series_fp)
    
    # create the zarr group
    data_zg = zarr.open(zarr_file)
    field_zarr = data_zg["raw"]
    field_shape = field_zarr.shape
    field_origin = field_zarr.attrs["field_origin"]
    
    # create zarr field for contours
    contours_zarr = data_zg.zeros("labels_" + label_name, shape=field_shape, dtype="uint64")
    
    # get unique ID for each trace
    name_ids = generateIDs(trace_names)

    # iterate through all sections and draw contours
    i = 0
    for snum, section in series.enumerateSections(
        message="Generating contours..."
    ):
        mag = section.mag
        tform = section.tforms["default"].getList()
        all_contours = {}
        for cname, contour in section.contours.items():
            if cname not in trace_names:
                continue
            else:
                for trace in contour:
                    id = name_ids[cname]
                    if id not in all_contours:
                        all_contours[id] = []
                    all_contours[id].append(trace.points)
        drawContoursinField(all_contours, tform, mag, contours_zarr, i, field_origin)
        i += 1
    
    print("Saving zarr atrributes...")
    
    # get values for saving zarr files
    xy_res = int(section.mag * 1000)
    z_res = int(section.thickness * 1000)
    resolution = [z_res, xy_res, xy_res]
    offset = [0, 0, 0]

    # save attributes
    contours_zarr.attrs["offset"] = offset
    contours_zarr.attrs["resolution"] = resolution

    series.close()

def getObjectNames(filepath : str) -> list:
    """Get the object names from a CSV file.
    
        Params:
            filepath (str): the filepath for the csv file
        Returns:
            (list) a list of names from the file
    """
    names = []
    with open(filepath, "r") as f:
        for line in f.readlines():
            names.append(line.strip())
    return names

jser_fp = input("Jser filepath: ")
os.chdir(os.path.dirname(jser_fp))
series = os.path.basename(jser_fp)

object_file = input("Object names filepath: ")
label_name = input("Desired label name: ")

objects = getObjectNames(object_file)

zarr_file = ""
for f in os.listdir("."):
    if f.endswith("data.zarr"):
        zarr_file = f
        break

if not zarr_file:
    jsonImagesToZarr(series)
    zarr_file = "data.zarr"

jsonContoursToZarr(series, objects, label_name, zarr_file)

print("\nDone!")