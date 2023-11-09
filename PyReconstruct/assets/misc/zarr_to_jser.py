import os
import sys
import cv2
import numpy as np
import zarr
import random

# add src modules to the system path
sys.path.append(os.path.join(os.getcwd(), "..", ".."))
from PyReconstruct.modules.datatypes import Series, Transform, Trace
from PyReconstruct.modules.backend.func import reducePoints

def getExteriors(mask : np.ndarray) -> list[np.ndarray]:
    """Get the exteriors from a mask.
    
        Params:
            mask (np.ndarray): the mask to extract exteriors from
        Returns:
            (list[np.ndarray]): the list of exteriors
    """
    cv_detected, hierarchy = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    exteriors = []
    for e in cv_detected:
        e = e[:,0,:]
        # invert the y axis
        e[:,1] *= -1
        e[:,1] += mask.shape[0]
        # reduce the points
        e = reducePoints(e, array=True)
        exteriors.append(e)
    return exteriors

def randomColor():
    """Return a random color (rgb or primary)."""
    r = random.randint(1, 6)
    if r == 1:
        return (255, 0, 0)
    elif r == 2:
        return (0, 255, 0)
    elif r == 3:
        return (0, 0, 255)
    elif r == 4:
        return (0, 255, 255)
    elif r == 5:
        return (255, 0, 255)
    elif r == 6:
        return (255, 255, 0)

# user-entered info
jser_fp = r"C:\Users\jfalco\Documents\Series\DSNYJ_JSER\DSNYJ.jser"
zarr_fp = r"C:\Users\jfalco\Documents\Series\DSNYJ_JSER\data.zarr"

# open the series and zarr
series = Series.openJser(jser_fp)
labels = zarr.open(os.path.join(zarr_fp, "labels"))

# get relevant information from zarr
window = labels.attrs["window"]
srange = labels.attrs["srange"]
mag = labels.attrs["true_mag"]
alignment = labels.attrs["alignment"]

colors = {}  # store colors for each id/object
for snum in range(*srange):
    section = series.loadSection(snum)
    arr = labels[snum - srange[0]]
    # iterate through unique labels
    for id in np.unique(arr):
        if id == 0:
            continue
        # get exteriors for the label
        exteriors = getExteriors(arr == id)
        for ext in exteriors:
            # convert to float
            ext = ext.astype(np.float64)
            # scale to actual coordinates
            ext *= mag
            # add origin
            ext[:,0] += window[0]
            ext[:,1] += window[1]
            # apply reverse transform
            tform = alignment[str(snum)])
            trace_points = tform.map(ext.tolist(), inverted=True)
            # get the trace color
            if id not in colors:
                colors[id] = randomColor()
            c = colors[id]               
            # create the trace and add to section
            trace = Trace(name=str(id), color=c)
            trace.points = trace_points
            section.addTrace(trace, log_message="Imported from autoseg data")
    section.save()

# save and close the series
series.saveJser()
series.close()

            




