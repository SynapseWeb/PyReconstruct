import os
import json

from constants.locations import backend_series_dir

from modules.pyrecon.series import Series

from modules.gui.gui_functions import progbar

def openJserFile(fp : str):
    """Process the file containing all section and series information.
    
        Params:
            fp (str): the filepath
    """
    with open(fp, "r") as f:
        jser_data = json.load(f)
    
    update, canceled = progbar(
        "Open Series",
        "Loading series..."
    )
    progress = 0
    final_value = len(jser_data)
    
    for filename in jser_data:
        filedata = jser_data[filename]
        backend_fp = os.path.join(backend_series_dir, filename)
        with open(backend_fp, "w") as f:
            json.dump(filedata, f)
        if filename.endswith(".ser"):
            series_fp = backend_fp
        
        if canceled():
            return None
        progress += 1
        update(progress/final_value * 100)
        
    return Series(series_fp)

def saveJserFile(save_fp : str, close=False):
    """Save the jser file."""
    jser_data = {}

    filenames = os.listdir(backend_series_dir)

    update, canceled = progbar(
        "Save Series",
        "Saving series...",
        cancel=False
    )
    progress = 0
    final_value = len(filenames)

    for filename in filenames:
        fp = os.path.join(backend_series_dir, filename)
        with open(fp, "r") as f:
            filedata = json.load(f)
        jser_data[filename] = filedata

        update(progress/final_value * 100)
        progress += 1
    
    with open(save_fp, "w") as f:
        json.dump(jser_data, f)
    
    if close:
        clearBackendSeries()
    
    update(100)

def clearBackendSeries():
    for f in os.listdir(backend_series_dir):
        os.remove(os.path.join(backend_series_dir, f))

def backendSeriesIsEmpty():
    return not bool(os.listdir(backend_series_dir))



