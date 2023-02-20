import os
import json
import shutil
from datetime import datetime

from constants.locations import createHiddenDir

from modules.pyrecon.series import Series
from modules.pyrecon.section import Section
from modules.pyrecon.transform import Transform

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

    sections = {}
    section_tforms = {}
    
    # iterate through json data
    for filename in jser_data:
        filedata = jser_data[filename]

        # ensure that filenames match the jser filename
        filename = sname + filename[filename.rfind("."):]
        backend_fp = os.path.join(hidden_dir, filename)

        if filename.endswith(".ser"):
            Series.updateJSON(filedata)  # update any missing attributes
            series_fp = backend_fp
        else:
            Section.updateJSON(filedata)  # update any missing attributes

            # gather the section numbers and section filenames
            snum = int(filename[filename.rfind(".")+1:])
            sections[snum] = filename

            # get transform data for the section
            tforms = {}
            for a in filedata["tforms"]:
                tforms[a] = Transform(filedata["tforms"][a])
            section_tforms[snum] = tforms
            
        with open(backend_fp, "w") as f:
            json.dump(filedata, f)
        
        if canceled():
            return None
        progress += 1
        update(progress/final_value * 100)
    
    # create and update the series
    series = Series(series_fp)
    series.sections = sections
    series.section_tforms = section_tforms
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

def moveSeries(new_jser_fp : str, series : Series, section : Section, b_section : Section):
    """Move/rename the series to its jser filepath.
    
        Params:
            new_jser_fp (str): the new location for the series
            series (Series): the series object
            section (Section): the section file being used
            b_section (Section): the secondary section file being used
        """
    # move/rename the hidden directory
    old_name = series.name
    new_name = os.path.basename(new_jser_fp)
    new_name = new_name[:new_name.rfind(".")]
    old_hidden_dir = os.path.dirname(series.filepath)
    new_hidden_dir = os.path.join(
        os.path.dirname(new_jser_fp),
        "." + new_name
    )
    shutil.move(old_hidden_dir, new_hidden_dir)

    # manually hide dir if windows
    if os.name == "nt":
        import subprocess
        subprocess.check_call(["attrib", "+H", new_hidden_dir])

    # rename all of the files
    for f in os.listdir(new_hidden_dir):
        if old_name in f:
            new_f = f.replace(old_name, new_name)
            os.rename(
                os.path.join(new_hidden_dir, f),
                os.path.join(new_hidden_dir, new_f)
            )
    
    # rename the series
    series.rename(new_name)

    # change the filepaths for the series and section files
    series.jser_fp = new_jser_fp
    series.hidden_dir = new_hidden_dir
    series.filepath = os.path.join(
        new_hidden_dir,
        os.path.basename(series.filepath).replace(old_name, new_name)
    )
    section.filepath = os.path.join(
        new_hidden_dir,
        os.path.basename(section.filepath).replace(old_name, new_name)
    )
    if b_section:
        b_section.filepath = os.path.join(
            new_hidden_dir,
            os.path.basename(b_section.filepath).replace(old_name, new_name)
        )