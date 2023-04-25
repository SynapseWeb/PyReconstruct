import os
import sys
import shutil
import traceback
import numpy as np
import cv2
import random
import zarr

from modules.datatypes import Series, Transform, Trace
from modules.backend.view import SectionLayer
from modules.backend.func import reducePoints

from PySide6.QtCore import (
    QRunnable,
    Slot,
    Signal,
    QObject,
    QThreadPool
)

# THREADING SOURCE: https://www.pythonguis.com/tutorials/multithreading-pyside6-applications-qthreadpool/

class WorkerSignals(QObject):
    '''
    Defines the signals available from a running worker thread.

    Supported signals are:

    finished
        No data

    error
        tuple (exctype, value, traceback.format_exc() )

    result
        object data returned from processing, anything

    progress
        int indicating % progress

    '''
    error = Signal(tuple)
    result = Signal(tuple)
    finished = Signal()


class Worker(QRunnable):
    '''
    Worker thread

    Inherits from QRunnable to handler worker thread setup, signals and wrap-up.

    :param callback: The function callback to run on this worker thread. Supplied args and
                     kwargs will be passed through to the runner.
    :type callback: function
    :param args: Arguments to pass to the callback function
    :param kwargs: Keywords to pass to the callback function

    '''

    def __init__(self, fn, *args):
        super(Worker, self).__init__()

        # Store constructor arguments (re-used for processing)
        self.fn = fn
        self.args = args
        self.signals = WorkerSignals()

    @Slot()
    def run(self):
        '''
        Initialise the runner function with passed args.
        '''

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args)
        except:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # Return the result of the processing
        finally:
            self.signals.finished.emit()


class Counter():

    def __init__(self, n : int, end_fn, *end_args):
        """Create the counter object.
        
            n (int): the threshold number that runs function when reached
            end_fn (function): the function that will be exectued when the list is complete
            *end_args: the arguments to include in the function when run
        """
        self.n = n
        self.count = 0
        self.fn = end_fn
        self.args = end_args
    
    def inc(self):
        """Add a number to the count.
            
            Params:
                n (int): the number to add to the count
        """
        self.count += 1
        if self.count == self.n:
            self.fn(*self.args)


def seriesToZarr(
        series : Series,
        groups : list[str],
        border_obj : str,
        srange : tuple,
        mag : float,
        finished_fn):
    """Convert a series into a zarr file usable by neuroglancer.
    
        Params:
            series (Series): the series to convert
            groups (list[str]): the group names to include in the zarr as labels
            border_obj (str): the object to use as the border marking
            srange (tuple): the range of sections (exclusive)
            mag (float): the microns per pixel for the zarr file
            finished_fn (function): the function to run when finished
    """
    # get the border window
    x_vals = []
    y_vals = []
    for snum in range(*srange):
        section = series.loadSection(snum)
        tform = section.tforms[series.alignment]
        if border_obj in section.contours:
            xmin, ymin, xmax, ymax = section.contours[border_obj].getBounds(tform)
            x_vals += [xmin, xmax]
            y_vals += [ymin, ymax]
    x = min(x_vals)
    w = max(x_vals) - x
    y = min(y_vals)
    h = max(y_vals) - y
    window = [x, y, w, h]

    # calculate field attributes
    shape = (
        srange[1] - srange[0],
        round(window[3]/mag),
        round(window[2]/mag)
    )
    pixmap_dim = shape[2], shape[1]  # the w and h of a 2D array

    # create the zarr files
    data_fp = os.path.join(
        os.path.dirname(series.jser_fp),
        "data.zarr"
    )
    if os.path.isdir(data_fp):  # delete existing data.zarr
        shutil.rmtree(data_fp)
    data_zg = zarr.open(data_fp, "a")
    data_zg["raw"] = zarr.empty(shape=shape, chunks=(1, 256, 256))
    for group in groups:
        data_zg[f"labels_{group}"] = zarr.empty(shape=shape, chunks=(1, 256, 256))
    
    # get values for saving zarr files (from last known section)
    z_res = int(section.thickness * 1000)
    xy_res = int(mag * 1000)
    resolution = [z_res, xy_res, xy_res]
    offset = [0, 0, 0]

    # get alignment of series
    alignment = {}
    for snum in range(*srange):
        alignment[str(snum)] = series.section_tforms[snum][series.alignment].getList()

    # save attributes
    data_zg["raw"].attrs["offset"] = offset
    data_zg["raw"].attrs["resolution"] = resolution 

    # save additional attributes for loading back into jser
    data_zg["raw"].attrs["window"] = window
    data_zg["raw"].attrs["srange"] = srange
    data_zg["raw"].attrs["true_mag"] = mag
    data_zg["raw"].attrs["alignment"] = alignment

    for group in groups:
        data_zg[f"labels_{group}"].attrs["offset"] = offset
        data_zg[f"labels_{group}"].attrs["resolution"] = resolution

        data_zg[f"labels_{group}"].attrs["window"] = window
        data_zg[f"labels_{group}"].attrs["srange"] = srange
        data_zg[f"labels_{group}"].attrs["true_mag"] = mag
        data_zg[f"labels_{group}"].attrs["alignment"] = alignment

    # create threadpool and interate through series
    threadpool = QThreadPool()
    threadpool.setMaxThreadCount(10)
    counter = Counter(
        len(range(*srange)),
        finished_fn,
        data_fp
    )
    for snum in range(*srange):
        worker = Worker(
            export_section,
            data_zg,
            snum,
            series,
            groups,
            srange,
            window,
            pixmap_dim,
            counter
        )
        threadpool.start(worker)
    
    return data_fp

def labelsToObjects(series : Series, data_fp : str, group : str, finished_fn):
    """Convert labels in a zarr file to objects in a series.
    
        Params:
            series (Series): the series to import zarr data into
            data_zg (str): the filepath for the zarr group
            group (str): the name of the group with labels of interest
            finished_fn (function): the function to run when finished
    """
    data_zg = zarr.open(data_fp)
    srange = data_zg["raw"].attrs["srange"]

    # create threadpool and iterate through sections
    colors = {}  # store colors for each id/object
    threadpool = QThreadPool()
    threadpool.setMaxThreadCount(10)
    counter = Counter(
        len(range(*srange)),
        finished_fn
    )
    for snum in range(*srange):
        worker = Worker(
            import_section,
            data_zg,
            group,
            snum,
            series,
            colors,
            counter
        )
        threadpool.start(worker)

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

def export_section(data_zg, snum, series, groups, srange, window, pixmap_dim, counter):
    print(f"Section {snum} exporting started")
    section = series.loadSection(snum)
    slayer = SectionLayer(section, series)
    z = snum - srange[0]
    arr = slayer.generateImageArray(
        pixmap_dim, 
        window
    )
    data_zg["raw"][z] = arr

    for group in groups:
        data_zg[f"labels_{group}"][z] = slayer.generateLabelsArray(
            pixmap_dim,
            window,
            series.object_groups.getGroupObjects(group)
        )
    print(f"Section {snum} exporting finished")
    counter.inc()

def import_section(data_zg, group, snum, series, colors, counter):
    print(f"Section {snum} importing started")
    # get relevant information from zarr
    labels = data_zg[group]
    offset = labels.attrs["offset"]
    resolution = labels.attrs["resolution"]

    raw = data_zg["raw"]
    window = raw.attrs["window"]
    srange = raw.attrs["srange"]
    mag = raw.attrs["true_mag"]
    alignment = raw.attrs["alignment"]

    # check if section was segmented
    z = snum - srange[0] - round(offset[0] / resolution[0])
    if not 0 <= z < labels.shape[0]:
        counter.inc()
        print(f"Section {snum} importing finished")
        return
    # load the section and data
    section = series.loadSection(snum)
    arr = labels[z]
    # iterate through unique labels
    for id in np.unique(arr):
        if id == 0:
            continue
        # get exteriors for the label
        exteriors = getExteriors(arr == id)
        for ext in exteriors:
            # convert to float
            ext = ext.astype(np.float64)
            # add offset to coordinates
            ext[:,0] += offset[2] / resolution[2]
            ext[:,1] += offset[1] / resolution[1]
            # scale to actual coordinates
            ext *= mag
            # add origin
            ext[:,0] += window[0]
            ext[:,1] += window[1]
            # apply reverse transform
            tform = Transform(alignment[str(snum)])
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
    print(f"Section {snum} importing finished")
    counter.inc()
