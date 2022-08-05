import daisy
import numpy as np
from PIL import Image
#from zarrgrid import ZarrGrid
#from skimage import measure
import cv2

def voxelToField(cv_contours, ysize, offset, resolution):
    # iterate through all points and convert
    new_contours = []
    for contour in cv_contours:
        new_contour = []
        for point in contour:
            x = point[0][0]
            y = ysize - point[0][1]
            new_point = ((x * resolution[2] + offset[2]) / 1000, 
                         (y * resolution[1] + offset[1]) / 1000)
            new_contour.append(new_point)
        new_contours.append(new_contour)
    return new_contours

def zarrToContours(labels_dataset, relative_offset, section_thickness, label_id):
    all_contours = {}
    labels_array = labels_dataset.to_ndarray()

    # get offset and resolution
    resolution = labels_dataset.voxel_size

    for section_num, array in enumerate(labels_array):

        # make boolean array
        array[array != label_id] = 0
        array = array.astype(np.uint8)
        ysize = array.shape[0]

        # get contour from boolean array
        #zarrgrid = ZarrGrid(array)
        #contours = zarrgrid.getAllContours()
        #contours = measure.find_contours(array)
        cv_contours = cv2.findContours(array, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]

        # convert x,y coordinates to field coordinates
        contours = voxelToField(cv_contours, ysize, relative_offset, resolution)

        all_contours[int(section_num + relative_offset[0]/section_thickness)] = contours
    
    return all_contours

def saveImages(zarr_fp):
    image_dataset = daisy.open_ds(zarr_fp, "clahe_raw/s2")
    image_array = image_dataset.to_ndarray()
    for i, array in enumerate(image_array):
        image = Image.fromarray(array)
        image.save(zarr_fp + "_" + str(i) + ".tif")

def getZarrObjects(zarr_fp, progbar=None):
    image_dataset = daisy.open_ds(zarr_fp, "clahe_raw/s2")
    image_roi = image_dataset.roi
    image_offset = image_roi.get_offset()

    labels_dataset = daisy.open_ds(zarr_fp, "labels/s2")
    label_ids = np.unique(labels_dataset.to_ndarray())
    labels_roi = labels_dataset.roi
    labels_offset = labels_roi.get_offset()

    relative_offset = [labels_offset[i] - image_offset[i] for i in range(len(labels_offset))]

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


