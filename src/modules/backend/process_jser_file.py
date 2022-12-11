import os
import json
from datetime import datetime

from constants.locations import createHiddenDir

from modules.pyrecon.series import Series

from modules.gui.gui_functions import progbar

def openJserFile(fp : str):
    """Process the file containing all section and series information.
    
        Params:
            fp (str): the filepath
    """
    # load json
    with open(fp, "r") as f:
        jser_data = json.load(f)
    
    # creating loading bar
    update, canceled = progbar(
        "Open Series",
        "Loading series..."
    )
    progress = 0
    final_value = len(jser_data)

    # create the hidden directory
    sdir = os.path.dirname(fp)
    sname = os.path.basename(fp)
    sname = sname[:sname.rfind(".")]
    hidden_dir = createHiddenDir(sdir, sname)
    
    # iterate through json data
    for filename in jser_data:
        filedata = jser_data[filename]
        backend_fp = os.path.join(hidden_dir, filename)
        with open(backend_fp, "w") as f:
            json.dump(filedata, f)
        if filename.endswith(".ser"):
            series_fp = backend_fp
        
        if canceled():
            return None
        progress += 1
        update(progress/final_value * 100)
        
    series = Series(series_fp)
    series.jser_fp = fp
    return series

def saveJserFile(series : Series, close=False):
    """Save the jser file."""
    jser_data = {}

    filenames = os.listdir(series.hidden_dir)

    update, canceled = progbar(
        "Save Series",
        "Saving series...",
        cancel=False
    )
    progress = 0
    final_value = len(filenames)

    for filename in filenames:
        if "." not in filename:  # skip the timer file
            continue
        fp = os.path.join(series.hidden_dir, filename)
        with open(fp, "r") as f:
            filedata = json.load(f)
        jser_data[filename] = filedata

        update(progress/final_value * 100)
        progress += 1
    
    save_str = json.dumps(jser_data)

    with open(series.jser_fp, "w") as f:
        f.write(save_str)
    
    # backup the series if requested
    if series.backup_dir and os.path.isdir(series.backup_dir):
        # get the file name
        fn = os.path.basename(series.jser_fp)
        # create the new file name
        t = datetime.now()
        dt = f"{t.year}{t.month:02d}{t.day:02d}_{t.hour:02d}{t.minute:02d}{t.second:02d}"
        fn = fn[:fn.rfind(".")] + "_" + dt + fn[fn.rfind("."):]
        # save the file
        backup_fp = os.path.join(
            series.backup_dir,
            fn
        )
        with open(backup_fp, "w") as f:
            f.write(save_str)
    else:
        series.backup_dir = ""
    
    if close:
        clearHiddenSeries(series)

    update(100)

def clearHiddenSeries(series : Series):
    if os.path.isdir(series.hidden_dir):
        for f in os.listdir(series.hidden_dir):
            os.remove(os.path.join(series.hidden_dir, f))
        os.rmdir(series.hidden_dir)



