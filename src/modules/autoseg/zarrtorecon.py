import daisy
import numpy as np
import cv2

from modules.calc.grid import reducePoints

def voxelToField(cv_contours : np.ndarray, ysize : float, offset : tuple, resolution : tuple) -> list:
    """Converts voxel coordinates to 2D field coordinates.
    
        Params:
            cv_contours (np.ndarray): the list of contours (returned from cv2.findContours)
            ysize (float): the y-length of the array
            offset (tuple): the offset to apply to the points
            resolution (tuple): the resolution to apply to the points
        Returns:
            (list) nested list of contour points
    """
    # iterate through all points and convert
    new_contours = []
    for contour in cv_contours:
        contour = contour[:,0].tolist()
        contour = reducePoints(contour)
        new_contour = []
        for point in contour:
            x = point[0]
            y = ysize - point[1]
            new_point = ((x * resolution[2] + offset[2]) / 1000, 
                         (y * resolution[1] + offset[1]) / 1000)
            new_contour.append(new_point)
        new_contours.append(new_contour)
    return new_contours

def zarrToContours(labels_dataset : daisy.Array, relative_offset : tuple, section_thickness : float, label_id) -> dict:
    """Convert zarr data for a specific label to a set of contours.
    
        Params:
            labels_dataset (daisy.Array): the labels data for the entire series
            relative_offset (tuple): the relative zyx offset for the labels to the image
            section_thickness (float): the section thickness in nanometers
            label_id: the unique id for the contour
        Returns:
            (dict): a list of contours for each section number
    """
    all_contours = {}
    labels_array = labels_dataset.to_ndarray()
    # get offset and resolution
    resolution = tuple(labels_dataset.voxel_size)
    for section_num, array in enumerate(labels_array):
        # make boolean array
        array[array != label_id] = 0
        array = array.astype(np.uint8)
        ysize = array.shape[0]
        # get contour from boolean array
        cv_contours = cv2.findContours(array, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)[0]
        # convert x,y coordinates to field coordinates
        contours = voxelToField(cv_contours, ysize, relative_offset, resolution)
        all_contours[int(section_num + relative_offset[0]/section_thickness)] = contours
    return all_contours

def saveZarrImages(zarr_fp : str, save_fp : str, resolution_label="s2") -> list:
    """Save the images contained in a zarr file in a given locations.
    
        Params:
            zarr_fp (str): the file path for the zarr file
            save_fp (str): the folder path to store the generated images
            resolution (str): the resolution folder within the zarr file to use
        Returns:
            (list) a list of the image filepaths
    """
    zarr_name = zarr_fp[zarr_fp.rfind("/")+1 : zarr_fp.rfind(".")]
    image_dataset = daisy.open_ds(zarr_fp, "clahe_raw/" + resolution_label)
    image_array = image_dataset.to_ndarray()
    image_fp_list = []
    for i, array in enumerate(image_array):
        image_fp = save_fp + "/" + zarr_name + "_" + str(i) + ".tif"
        cv2.imwrite(image_fp, array)
        image_fp_list.append(image_fp)
    return image_fp_list

def getZarrObjects(zarr_fp : str, resolution_label="s2", progbar=None) -> dict:
    """Returns zarr objects as a set of contours.
    
        Params:
            zarr_fp (str): the filepath for the zarr file
            progbar (QProgressDialog): the progress bar dialog
        Returns:
            (dict) a list of contours by id number
        """
    # get image data and offset
    image_dataset = daisy.open_ds(zarr_fp, "clahe_raw/" + resolution_label)
    image_roi = image_dataset.roi
    image_offset = image_roi.get_offset()
    # get labels data and offset
    labels_dataset = daisy.open_ds(zarr_fp, "labels/" + resolution_label)
    label_ids = np.unique(labels_dataset.to_ndarray())
    labels_roi = labels_dataset.roi
    labels_offset = labels_roi.get_offset()
    # calculate relative offset from labels to images
    relative_offset = tuple([labels_offset[i] - image_offset[i] for i in range(len(labels_offset))])
    # store all contour data
    objects = {}
    if progbar is not None:
        final_value = len(label_ids)
        progress = 0
    for id in label_ids:
        contours = zarrToContours(labels_dataset, relative_offset, 50, id)
        objects[int(id)] = contours
        if progbar is not None:
            if progbar.wasCanceled(): return
            progress += 1
            progbar.setValue(progress/final_value * 100)
    return objects

