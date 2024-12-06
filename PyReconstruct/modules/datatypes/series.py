import os
import re
import json
import shutil
from datetime import datetime
from copy import deepcopy
from pathlib import Path
from typing import Union

from PySide6.QtCore import QSettings

from .log import LogSet, LogSetPair
from .ztrace import Ztrace
from .section import Section
from .trace import Trace
from .transform import Transform
from .obj_group_dict import ObjGroupDict
from .series_data import SeriesData
from .objects import Objects, SeriesObject
from .default_settings import default_settings, default_series_settings
from .host_tree import HostTree

from PyReconstruct.modules.constants import (
    createHiddenDir,
    welcome_series_dir,
    getDateTime
)
from PyReconstruct.modules.constants import welcome_series_dir, default_traces
from PyReconstruct.modules.gui.utils import getProgbar


class Series():
    
    qsettings_defaults = default_settings.copy()
    qsettings_series_defaults = default_series_settings.copy()

    def __init__(self, filepath : str, sections : dict, get_series_data=True):
        """Load the series file.

        (This function is not used to open a JSER file.)
        
            Params:
                filepath (str): the filepath for the series JSON file
                sections (dict): section basename for each section
                get_series_data (bool): True if series data should be loaded
        """
        self.filepath = filepath
        self.sections = sections
        self.name = os.path.basename(self.filepath)[:-4]

        with open(filepath, "r") as f:
            series_data = json.load(f)

        Series.updateJSON(series_data)

        self.jser_fp = ""
        self.hidden_dir = os.path.dirname(self.filepath)
        self.modified = False

        self.current_section = series_data["current_section"]
        self.src_dir = series_data["src_dir"]
        self.screen_mag = 0  # default value for screen mag (will be calculated when generateView called)
        self.window = series_data["window"]
        self.palette_traces = dict((
            (name, [Trace.fromList(trace) for trace in palette_group])
            for name, palette_group in series_data["palette_traces"].items()
        ))
        self.palette_index = series_data["palette_index"]

        self.ztraces = series_data["ztraces"]
        for name in self.ztraces:
            self.ztraces[name] = Ztrace.fromDict(name, self.ztraces[name])

        self.alignment = series_data["alignment"]
        
        self.object_groups = ObjGroupDict(self, "objects", series_data["object_groups"])
        self.groups_visibility = self.initGroupViz()

        self.ztrace_groups = ObjGroupDict(self, "ztraces", series_data["ztrace_groups"])

        self.obj_attrs = series_data["obj_attrs"]
        self.ztrace_attrs = series_data["ztrace_attrs"]

        self.bc_profile = series_data["current_brightness_contrast_profile"]

        # default settings
        self.modified_ztraces = set()
        self.modified_objects = set()
        self.leave_open = False

        # possible zarr overlay
        self.zarr_overlay_fp = None
        self.zarr_overlay_group = None

        self.options = series_data["options"]

        # possible existing log set
        if "log_set" in series_data:
            self.log_set = LogSet.fromList(series_data["log_set"])
        else:
            self.log_set = LogSet()

        # keep track of relevant overall series data
        self.data = SeriesData(self)
        if get_series_data:
            self.data.refresh()

        # objects for non-GUI users
        self.objects = Objects(self)

        # editors list
        self.editors = set(series_data["editors"])
        if not self.isWelcomeSeries() and not self.editors:
            self.editors = self.getEditorsFromHistory()

        # series code
        self.code = series_data["code"]

        # user-defined columns
        self.user_columns = series_data["user_columns"]

        # host tree
        self.host_tree = HostTree(series_data["host_tree"], self)

        ## Group visibility
        self.groups_visibility = self.initGroupViz()

    def __enter__(self):
        
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        
        if exc_type is not None:
            traceback.print_exception(exc_type, exc_value, traceback)

        self.close()
    
    ## OPENING, LOADING, AND MOVING THE JSER FILE
    @staticmethod
    def openJser(fp : str):
        """Process the file containing all section and series information.
        
            Params:
                fp (str): the filepath to the jser
            Returns:
                (Series): the series object created from the jser
        """
        # check for existing hidden folder
        sdir = os.path.dirname(fp)
        sname = os.path.basename(fp)
        sname = sname[:sname.rfind(".")]
        hidden_dir = os.path.join(sdir, f".{sname}")
        ser_filepath = os.path.join(hidden_dir, f"{sname}.ser")
        if os.path.isdir(hidden_dir) and os.path.isfile(ser_filepath):
            # gather sections
            sections = {}
            for f in os.listdir(hidden_dir):
                if "." not in f:
                    continue
                ext = f[f.rfind(".")+1:]
                if ext.isnumeric():
                    snum = int(ext)
                    sections[snum] = f
            series = Series(ser_filepath, sections)
            series.jser_fp = fp
            series.leave_open = True
            return series

        # load json
        with open(fp, "r") as f:
            jser_data = json.load(f)
        
        # UPDATE FROM OLD JSER FORMATS
        updated_jser_data = {}
        sections_dict = {}
        if "sections" not in jser_data and "series" not in jser_data:
            # gather the sections and section numbers
            for key in jser_data:
                # key could just be the extension OR the name + extension
                if "." in key:
                    ext = key[key.rfind(".")+1:]
                else:
                    ext = key
                # check if section or series data
                if ext.isnumeric():
                    snum = int(ext)
                    sections_dict[snum] = jser_data[key]
                else:
                    updated_jser_data["series"] = jser_data[key]
            # organize the sections in a list
            sections_list = [None] * (max(sections_dict.keys())+1)
            for snum, sdata in sections_dict.items():
                sections_list[snum] = sdata
            updated_jser_data["sections"] = sections_list
            # replace data
            jser_data = updated_jser_data
        
        # UPDATE TO INCLUDE A LOG
        if "log" not in jser_data:
            jser_data["log"] = "Date, Time, User, Obj, Sections, Event"
        
        # creating loading bar
        progbar = getProgbar(
            text="Opening series..."
        )
        progress = 0
        final_value = 0
        for sdata in jser_data["sections"]:
            if sdata: final_value += 1
        final_value *= 2  # for loading section data
        final_value += 2  # unpacking series and log

        # create the hidden directory
        hidden_dir = createHiddenDir(sdir, sname)
        
        # extract JSON series data
        series_data = jser_data["series"]
        # add empty log_set for opening/saving purposes
        series_data["log_set"] = []
        Series.updateJSON(series_data)
        series_fp = os.path.join(hidden_dir, sname + ".ser")
        with open(series_fp, "w") as f:
            json.dump(series_data, f)
        if progbar.wasCanceled():
            return None
        progress += 1
        progbar.setValue(progress/final_value * 100)

        # extract JSON section data
        sections = {}
        for snum, section_data in enumerate(jser_data["sections"]):
            # check for empty section, skip if so
            if section_data is None:
                continue

            filename = sname + "." + str(snum)
            section_fp = os.path.join(hidden_dir, filename)

            Section.updateJSON(section_data, snum)  # update any missing attributes
            
            section_data["align_locked"] = True  # lock the section

            # gather the section numbers and section filenames
            sections[snum] = filename
                
            with open(section_fp, "w") as f:
                json.dump(section_data, f)
            
            if progbar.wasCanceled():
                return None
            progress += 1
            progbar.setValue(progress/final_value * 100)
        
        # extract the existing log
        log_str = jser_data["log"]
        existing_log_fp = os.path.join(hidden_dir, "existing_log.csv")
        with open(existing_log_fp, "w") as f:
            f.write(log_str)
        if progbar.wasCanceled():
            return None
        progress += 1
        progbar.setValue(progress/final_value * 100)
        
        # create the series
        series = Series(series_fp, sections, get_series_data=False)
        series.jser_fp = fp

        # gather the series data
        for snum, section in series.enumerateSections(show_progress=False):
            series.data.updateSection(section, update_traces=True, log_events=False)
            if progbar.wasCanceled():
                return None
            progress += 1
            progbar.setValue(progress/final_value * 100)
        
        return series

    def saveJser(self, save_fp : str = None, close : bool = False):
        """Save the jser file.
        
            Params:
                save_fp (str): the optional override filepath to save the jser file
                close (bool): True if series should be closed after saving
        """
        self.save()

        jser_data = {}

        filenames = os.listdir(self.hidden_dir)

        progbar = getProgbar(
            text="Saving series...",
            cancel=False
        )
        progress = 0
        final_value = len(filenames)

        # get the max section number
        sections_len = max(self.sections.keys())+1
        jser_data["sections"] = [None] * sections_len
        jser_data["series"] = {}
        jser_data["log"] = ""

        for filename in filenames:
            if "." not in filename:  # skip the timer file
                continue
            ext = filename[filename.rfind(".")+1:]
            fp = os.path.join(self.hidden_dir, filename)

            if ext.isnumeric():
                with open(fp, "r") as f:
                    filedata = json.load(f)
                jser_data["sections"][int(ext)] = filedata
            elif ext == "ser":
                with open(fp, "r") as f:
                    filedata = json.load(f)
                # manually remove log set from series data if exists
                if filedata.get("log_set"): del(filedata["log_set"])
                # add the log_set string to the log
                log_set_str = str(self.log_set)
                if log_set_str:
                    jser_data["log"] += "\n" + str(self.log_set)
                # save the series
                jser_data["series"] = filedata
            elif filename == "existing_log.csv":
                with open(fp, "r") as f:
                    existing_log = ""
                    for line in f.readlines():
                        if line.strip():
                            existing_log += line
                # continue saving the existing log file
                jser_data["log"] = existing_log + jser_data["log"]

            progbar.setValue(progress/final_value * 100)
            progress += 1
        
        save_str = json.dumps(jser_data)

        jser_fp = self.jser_fp if not save_fp else save_fp
        with open(jser_fp, "w") as f:
            f.write(save_str)
        
        if close:
            self.close()

        progbar.setValue(100)
    
    def move(self, new_jser_fp : str, section : Section = None, b_section : Section = None):
        """Move/rename the series to its jser filepath.
        
            Params:
                new_jser_fp (str): the new location for the series
                section (Section): the section file being used (in GUI)
                b_section (Section): the secondary section file being used (in GUI)
            """
        
        ## Move/Rename hidden directory
        old_name = self.name
        new_name = os.path.basename(new_jser_fp)
        new_name = new_name[:new_name.rfind(".")]

        old_hidden_dir = os.path.dirname(self.filepath)

        new_hidden_dir = os.path.join(
            os.path.dirname(new_jser_fp),
            "." + new_name
        )

        shutil.move(old_hidden_dir, new_hidden_dir)

        ## Manually hide dir if Windows
        if os.name == "nt":
            import subprocess
            subprocess.check_call(["attrib", "+H", new_hidden_dir])

        ## Rename all files
        for f in os.listdir(new_hidden_dir):
            if old_name in f:
                new_f = f.replace(old_name, new_name)
                os.rename(
                    os.path.join(new_hidden_dir, f),
                    os.path.join(new_hidden_dir, new_f)
                )
        
        ## Rename series
        self.rename(new_name)

        ## Update filepaths in series and section files
        self.jser_fp = new_jser_fp
        self.hidden_dir = new_hidden_dir
        
        self.filepath = os.path.join(
            new_hidden_dir,
            os.path.basename(self.filepath).replace(old_name, new_name)
        )

        ## Update loaded sections in GUI
        if section:
            section.filepath = os.path.join(
                new_hidden_dir,
                os.path.basename(section.filepath).replace(old_name, new_name)
            )
            
        if b_section:
            b_section.filepath = os.path.join(
                new_hidden_dir,
                os.path.basename(b_section.filepath).replace(old_name, new_name)
            )
    
    def close(self):
        """Clear the hidden directory of the series."""
        
        if self.isWelcomeSeries() or self.leave_open:
            return
        
        if os.path.isdir(self.hidden_dir):
            
            for f in os.listdir(self.hidden_dir):
                os.remove(os.path.join(self.hidden_dir, f))
                
            os.rmdir(self.hidden_dir)
    
    @staticmethod
    def updateJSON(series_data : dict):
        """Add missing attributes to the series JSON.

        (Updates the dictionary in place)
        
            Params:
                series_data (dict): the JSON data to update
        """
        empty_series = Series.getEmptyDict()
        for key in empty_series:
            if key not in series_data:
                series_data[key] = empty_series[key]
        for key in empty_series["options"]:
            if key not in series_data["options"]:
                series_data["options"][key] = empty_series["options"][key]
        for key in list(series_data["options"].keys()):
            if key not in empty_series["options"]:
                del series_data["options"][key]
        
        # check for backup_dir key
        if "backup_dir" in series_data:
            del series_data["backup_dir"]
        
        # check the ztraces
        if type(series_data["ztraces"]) is list:
            ztraces_dict = {}
            for ztrace in series_data["ztraces"]:
                # check for missing color attribute
                if "color" not in ztrace:
                    ztrace["color"] = (255, 255, 0)
                # convert to dictionary format
                name = ztrace["name"]
                ztraces_dict[name] = {}
                del(ztrace["name"])
                ztraces_dict[name] = ztrace
            series_data["ztraces"] = ztraces_dict
        
        # check the traces (convert dicts to lists) if old format of trace palette (single trace palette)
        if type(series_data["palette_traces"]) is list:
            for i, trace in enumerate(series_data["palette_traces"]):
                if type(trace) is dict:
                    trace = [
                        trace["name"],
                        trace["x"],
                        trace["y"],
                        trace["color"],
                        trace["closed"],
                        trace["negative"],
                        trace["hidden"],
                        trace["mode"],
                        trace["tags"],
                    ]
                    series_data["palette_traces"][i] = trace
                # remove history from trace if it exists
                elif len(trace) == 10:
                    trace.pop()
                # check for trace mode
                if type(trace[7]) is not list:
                    trace[7] = ["none", "none"]

        # check for palette reformatting
        if "current_trace" in series_data:
            del(series_data["current_trace"])
            series_data["palette_traces"] = {"palette1": series_data["palette_traces"]}
            series_data["palette_index"] = ["palette1", 0]
        
        # check the window
        window = series_data["window"]
        if window[2] == 0:  # width
            window[2] = 1
        if window[3] == 0:  # height
            window[3] == 1
        
        # check for separate obj attrs
        if "obj_attrs" not in series_data:
            series_data["obj_attrs"] = {}
        obj_attrs = series_data["obj_attrs"]
        if "object_3D_modes" in series_data:
            for obj_name, modes in series_data["object_3D_modes"].items():
                if obj_name not in obj_attrs:
                    obj_attrs[obj_name] = {}
                obj_attrs[obj_name]["3D_modes"] = modes
        if "last_user" in series_data:
            for obj_name, last_user in series_data["last_user"].items():
                if obj_name not in obj_attrs:
                    obj_attrs[obj_name] = {}
                obj_attrs[obj_name]["last_user"] = last_user
        if "curation" in series_data:
            for obj_name, curation in series_data["curation"].items():
                if obj_name not in obj_attrs:
                    obj_attrs[obj_name] = {}
                if "curation" not in obj_attrs[obj_name]:  # do not overwrite existing curation
                    obj_attrs[obj_name]["curation"] = curation
        
        # check for brightnes_contrast profile
        if "current_brightness_contrast_profile" not in series_data:
            series_data["current_brightness_contrast_profile"] = "default"
        
        # check for splitting 3D modes
        for name, data in series_data["obj_attrs"].items():
            if "3D_modes" in data:
                data["3D_mode"] = data["3D_modes"][0]
                data["3D_opacity"] = data["3D_modes"][1]
                del(data["3D_modes"])
        
        # check for editors list
        if "editors" not in series_data:
            series_data["editors"] = []

    def getDict(self) -> dict:
        """Convert series object into a dictionary.
        
            Returns:
                (dict): all of the compiled section data
        """
        d = {}
        
        d["current_section"] = self.current_section
        d["src_dir"] = self.src_dir
        d["window"] = self.window
        
        d["palette_traces"] = dict((
            (name, [trace.getList() for trace in palette_group])
            for name, palette_group in self.palette_traces.items()
        ))
        d["palette_index"] = self.palette_index

        d["ztraces"] = {}
        for name in self.ztraces:
            d["ztraces"][name] = self.ztraces[name].getDict()
            
        d["alignment"] = self.alignment
        d["object_groups"] = self.object_groups.getGroupDict()
        d["ztrace_groups"] = self.ztrace_groups.getGroupDict()

        d["obj_attrs"] = self.obj_attrs
        d["ztrace_attrs"] = self.ztrace_attrs

        d["current_brightness_contrast_profile"] = self.bc_profile

        # ADDED SINCE JAN 25TH
        d["options"] = self.options

        d["log_set"] = self.log_set.getList()

        d["editors"] = list(self.editors)
        d["code"] = self.code
        d["user_columns"] = self.user_columns
        d["host_tree"] = self.host_tree.getDict()

        return d
    
    @staticmethod
    def getEmptyDict() -> dict:
        """Get an empty dictionary for a series object.
        
            Returns:
                (dict): the empty series dictionary
        """
        series_data = {}
        
        # series_data["sections"] = {}  # section_number : section_filename
        series_data["current_section"] = 0  # last section left off
        series_data["src_dir"] = ""  # the directory of the images
        series_data["window"] = [0, 0, 1, 1] # x, y, w, h of reconstruct window in field coordinates
        series_data["palette_traces"] = {
            "palette1": [t.getList(include_name=True) for t in Series.getDefaultPaletteTraces()]
        }
        series_data["palette_index"] = ["palette1", 0]
        series_data["ztraces"] = []
        series_data["alignment"] = "default"
        series_data["object_groups"] = {}
        series_data["ztrace_groups"] = {}
        series_data["current_brightness_contrast_profile"] = "default"

        # ADDED SINCE JAN 25TH

        series_data["options"] = {
            # table columns (default display)
            # note: "static" columns are *always* displayed and are not included here.
            # See gui/table/trace.py for static cols
            # MFO = modifiable from options
            "object_columns": list({  # MFO
                
                "Range"        : True,
                "Count"        : False,
                "Flat area"    : False,
                "Volume"       : False,
                "Radius"       : False,
                "Host"         : True,
                "Superhosts"   : False,
                "Groups"       : True,
                "Trace tags"   : False,
                "Locked"       : True,
                "Last user"    : True,
                "Curate"         : False,
                "Alignment"      : False,
                "Comment"        : True,
                "Configuration"  : False
                
            }.items()),
            
            "trace_columns": list({  # MFO
                
                "Index"        : False,
                "Tags"         : True,
                "Hidden"       : True,
                "Closed"       : True,
                "Length"       : True,
                "Area"         : True,
                "Radius"       : True,
                "Centroid"     : False,
                "Feret"        : False,
                
            }.items()),
            
            "flag_columns": list({  # MFO
                
                "Section"      : True,
                "Color"        : True,
                "Flag"         : True,
                "Resolved"     : False,
                "Last Comment" : True
                
            }.items()),
            
            "section_columns": list({  # MFO
                
                "Thickness"    : True,
                "Locked"       : True,
                "Brightness"   : True,
                "Contrast"     : True,
                "Image Source" : True
                
            }.items()),
            
            "ztrace_columns": list({  # MFO
                
                "Start"        : True,
                "End"          : True,
                "Distance"     : True,
                "Groups"       : True,
                "Alignment"    : True
                
            }.items()),

            # distances
            "small_dist"       : 0.01,  # MFO
            "med_dist"         : 0.1,  # MFO
            "big_dist"         : 1,  # MFO
            "autoseg"          : {},
            
        }

        series_data["obj_attrs"] = {}
        series_data["ztrace_attrs"] = {}

        series_data["editors"] = []
        series_data["code"] = ""
        series_data["user_columns"] = {}
        series_data["host_tree"] = {}

        return series_data
    
    @staticmethod
    def new(image_locations : list, series_name : str, mag : float, thickness : float):
        """Create a new blank series.
        
            Params:
                image_locations (list): the paths for each image
                series_name (str): user-entered series name
                mag (float): the microns per pixel for the series
                thickness (float): the section thickness
            Returns:
                (Series): the newly created series object
        """
        try:
            
            wdir = os.path.dirname(image_locations[0])
            
            if "zarr" in wdir:  # create series next to zarr if necessary
                
                src_dir = wdir[:wdir.rfind("zarr") + len("zarr")]
                wdir = os.path.dirname(src_dir)
                
            else:
                
                src_dir = wdir
                
            hidden_dir = createHiddenDir(wdir, series_name)
            
        except PermissionError:
            
            print(
                "Series cannot be created adjacent to images due "
                "to user not having proper permissions. Creating "
                "in home folder instead."
            )
            
            if os.name == "nt":
                
                wdir = os.environ.get("HOMEPATH")
                
            else:
                
                wdir = os.environ.get("HOME")
                
            hidden_dir = createHiddenDir(wdir, series_name)

        series_data = Series.getEmptyDict()
        series_data["src_dir"] = src_dir  # img dir
        sections = {}

        for i, _ in enumerate(image_locations):
            sections[i] = series_name + "." + str(i)

        series_fp = os.path.join(hidden_dir, series_name + ".ser")
        
        with open(series_fp, "w") as series_file:
            series_file.write(json.dumps(series_data, indent=2))
        
        ## Create section files (.number files)
        for i, img in enumerate(image_locations):
            Section.new(series_name, i, img, mag, thickness, hidden_dir)

        ## Create empty existing_log.csv file
        existing_log_path = os.path.join(hidden_dir, "existing_log.csv")
        with open(existing_log_path, "w") as f:
            f.write("Date, Time, User, Obj, Sections, Event")

        ## Create series object
        series = Series(series_fp, sections)
        
        # save the jser file
        # series.jser_fp = os.path.join(
        #     wdir,
        #     f"{series_name}.jser"
        # )
        # series.saveJser()

        ## Create initial log
        series.addLog(None, None, "Create series")
        
        return series
    
    def isWelcomeSeries(self) -> bool:
        """Return True if self is the welcome series.
        
            Returns:
                (bool): True if this series is the wolcome series
        """
        try:
            if os.path.samefile(self.filepath, os.path.join(welcome_series_dir, "welcome.ser")):
                return True
            else:
                return False
            
        except FileNotFoundError:
            return False
        
    def save(self):
        """Save file into json."""
        if self.isWelcomeSeries():
            return

        d = self.getDict()
        with open(self.filepath, "w") as f:
            f.write(json.dumps(d, indent=1))
    
    def getwdir(self) -> str:
        """Get the working directory of the series.
        
            Returns:
                (str): the directory containing the series
        """
        return os.path.dirname(self.filepath)
    
    def loadSection(self, section_num : int) -> Section:
        """Load a section object.
        
            Params:
                section_num (int): the section number
            Returns:
                (Section): the section
        """
        section = Section(section_num, self)
        return section
    
    def enumerateSections(self, show_progress : bool = True, message : str = "Loading series data...", series_states=None, breakable=True):
        """Allow iteration through the sections.

        Proper use in a for loop: for snum, section in series.enumerateSections():
        
            Params:
                show_progress (bool): True if progress should be displayed
                message (str): the message to display by the progress bar
                series_states (dict): section number : SectionStates object (use with GUI for undo/redo)
                breakable (bool): True if sereis state is breakable
            Returns:
                (SeriesIterator): an iterable object for for loops
        """
        return SeriesIterator(self, show_progress, message, series_states, breakable)

    def modifyAlignments(self, alignment_dict : dict, series_states=None, log_event=True):
        """Modify the series's alignment.

        Accepts input from dialog. Note: Do not use this method outside of
        the user interface.
        
            Params:
                alignment_dict (dict): returned from the alignment dialog
                series_states (dict): optional dict of undo states for GUI
                log_event (bool): True if event should be logged
        """
        # change the current alignment if necessary
        if self.alignment != "no-alignment" and alignment_dict[self.alignment] is None:
            self.alignment = "no-alignment"

        for snum, section in self.enumerateSections(
            message="Modifying alignments...",
            series_states=series_states,
            breakable=False
        ):
            old_tforms = section.tforms.copy()
            new_tforms = {}
            for new_a, old_a in alignment_dict.items():
                if old_a is None or old_a not in old_tforms:
                    continue
                else:
                    new_tforms[new_a] = old_tforms[old_a]
            section.tforms = new_tforms
            section.save()
        
        if log_event:
            for new_a, old_a in alignment_dict.items():
                if new_a == old_a:
                    continue
                if old_a is None and new_a in old_tforms and new_a not in alignment_dict.values():
                    self.addLog(None, None, f"Delete alignment {new_a}")
                elif old_a == self.alignment:
                    self.addLog(None, None, f"Create alignment {new_a} from {old_a}")
                elif old_a in old_tforms and new_a not in old_tforms:
                    self.addLog(None, None, f"Rename alignment {old_a} to {new_a}")
    
    def modifyBCProfiles(self, profiles_dict : dict, log_event=True):
        """Modify the series's brightness/contrast profiles.

        Accepts input from dialog. Note: Do not use this method outside of
        the user interface.
        
            Params:
                profiles_dict (dict): returned from the bc_profiles dialog
                log_event (bool): True if event should be logged
        """
        for _, section in self.enumerateSections(
            message="Modifying brightness/contrast profiles..."
        ):
            old_profiles = section.bc_profiles.copy()
            new_profiles = {}
            for new_p, old_p in profiles_dict.items():
                if old_p is None:
                    continue
                elif old_p not in old_profiles:
                    continue
                else:
                    new_profiles[new_p] = old_profiles[old_p]
            section.bc_profiles = new_profiles
            section.save()
        
        if log_event:
            for new_p, old_p in profiles_dict.items():
                if new_p == old_p:
                    continue
                if old_p is None and new_p in old_profiles and new_p not in profiles_dict.values():
                    self.addLog(None, None, f"Delete brightness/contrast profile {new_p}")
                elif old_p == self.alignment:
                    self.addLog(None, None, f"Create brightness/contrast profile {new_p} from {old_p}")
                elif old_p in old_profiles and new_p not in old_profiles:
                    self.addLog(None, None, f"Rename brightness/contrast profile {old_p} to {new_p}")
    
    def getZValues(self):
        """Return z-coordinates for each section.

        Notes: This method is primarily for 3D use.
        
            Returns:
                (dict): section number : z-value
        """
        zvals = {}
        z = 0
        for snum in sorted(self.sections.keys()):
            t = self.data["sections"][snum]["thickness"]
            z += t
            zvals[snum] = z
        
        return zvals
    
    def createZtrace(self, obj_name : str, cross_sectioned : bool = True, log_event=True):
        """Create a ztrace from an existing object in the series.
        
            Params:
                obj_name (str): the name of the object to create the ztrace from
                cross_sectioned (bool): True if one ztrace point per section, False if multiple per section
                log_event (bool): True if event should be logged
        """
        ztrace_name = f"{obj_name}_zlen"
        ztrace_color = (0, 0, 0)  # default to black

        ## Remove existing ztrace with same name
        
        if ztrace_name in self.ztraces:
            del(self.ztraces[ztrace_name])
        
        ## If create on midpoints, make one point per section

        if cross_sectioned:
            
            points = []
            
            for snum, section in self.enumerateSections(
                message="Creating ztrace..."
            ):
                
                if obj_name in section.contours:
                    
                    contour = section.contours[obj_name]
                    p = (*contour.getMidpoint(), snum)
                    points.append(p)
                    
        ## Otherwise, make points by trace history by section. Each trace gets
        ## its own point, ztrace points made in chronological order of trace
        ## history. (Accomodates obliquely and longitudinally sectioned objects.
        
        else:
            
            points = []

            for snum, section in self.enumerateSections(
                message="Creating ztrace..."
            ):
                
                if obj_name in section.contours:
                    
                    contour = section.contours[obj_name]

                    for trace in contour:
                        # get the midpoint
                        p = (*trace.getMidpoint(), snum)
                        points.append(p)
        
        self.ztraces[ztrace_name] = Ztrace(
            ztrace_name,
            ztrace_color,
            points
        )

        ## Assign obj alingment to new ztrace
        
        obj_align = self.getAttr(obj_name, "alignment")
        self.setAttr(ztrace_name, "alignment", obj_align, ztrace=True)

        ## Set modified and log event
        
        self.modified_ztraces.add(ztrace_name)

        if log_event:
            self.addLog(ztrace_name, None, "Create ztrace")

        self.modified = True
    
    def editZtraceAttributes(self, name : str, new_name : str, new_color : tuple, log_event=True):
        """Edit the name and color of a ztrace.
        
            Params:
                name (str): the original ztrace name
                new_name (str): the new name
                new_color (tuple): the new color
                log_event (bool): True if event should be logged
        """
        # modify the ztrace data
        ztrace = self.ztraces[name]
        if new_name:
            ztrace.name = new_name
            if new_name != name:  # if renamed
                del(self.ztraces[name])
                self.ztraces[new_name] = ztrace
                # update group data
                groups = self.ztrace_groups.getObjectGroups(name)
                for g in groups:
                    self.ztrace_groups.add(g, new_name)
                self.ztrace_groups.removeObject(name)
        if new_color:
            ztrace.color = new_color
        
        self.modified = True
        self.modified_ztraces.add(name)
        self.modified_ztraces.add(new_name)
        
        if log_event:
            if new_name != name:
                self.addLog(name, None, f"Rename ztrace to {new_name}")
                self.addLog(new_name, None, f"Create ztrace from {name}")
            else:
                self.addLog(name, None, "Modify ztrace")
    
    def smoothZtraces(self, names : list, smooth : int, newztrace : bool, log_event=True):
        """Smooth a set of ztraces.
        
            Params:
                names (list): the names of the ztraces to smooth
                smooth (int): the smoothing factor
                newztrace (bool): False if ztrace should be overwritten
        """
        ## Smooth ztraces
        for name in names:

            
            
            ## Create new ztrace if requested
            if newztrace:
                
                ztrace = self.ztraces[name].copy()
                ztrace_align = self.getAttr(name, "alignment", ztrace=True)
                
                new_name = f"{ztrace.name}_smooth{smooth}"

                ztrace.name = new_name
                self.ztraces[new_name] = ztrace
                self.setAttr(new_name, "alignment", ztrace_align, ztrace=True)
                
            else:
                
                ztrace = self.ztraces[name]
                
            ztrace.smooth(self, smooth)
            
            self.modified_ztraces.add(ztrace.name)
        
            if log_event:
                self.addLog(name, None, "Smooth ztrace")

    def deleteZtraces(self, names : list, log_event=True):
        """Delete a list of ztraces:
            Params:
                names (list): the names of the ztraces
        """
        for name in names:
            del(self.ztraces[name])
            self.modified_ztraces.add(name)
            self.ztrace_groups.removeObject(name)

            if log_event:
                self.addLog(name, None, "Delete ztrace")
        
    def rename(self, new_name : str):
        """Rename the series.
        
            Params:
                new_name (str): the new name for the series
        """
        old_name = self.name
        for snum in self.sections:
            sname = self.sections[snum]
            self.sections[snum] = sname.replace(old_name, new_name)
        self.name = new_name

    #### Series-wide trace functions ###############################################################
    
    def deleteObjects(self, obj_names : list, series_states=None):
        """Delete object(s) from the series.
        
            Params:
                obj_names (list): the objects to delete
                series_states (dict): for use with GUI states
        """
        for snum, section in self.enumerateSections(
            message="Deleting object(s)...",
            series_states=series_states
        ):
            modified = False
            for obj_name in obj_names:
                if obj_name in section.contours:
                    for trace in section.contours[obj_name]:
                        section.removeTrace(trace)
                    del(section.contours[obj_name])
                    modified = True
            
            if modified:
                section.save()  # deleting object will automatically be logged
        
        self.modified = True

    def copyObjects(self, obj_names: list, series_states=None, log_event=True) -> list:
        """Copy object(s) from the series

            Params:
                obj_names (list): the objects to delete
                series_states (dict): for use with GUI states

        """

        if log_event:

            for obj_name in obj_names:
                self.addLog(obj_name, None, f"Create copy {obj_name}_copy")

        for snum, section in self.enumerateSections(
                message="Copying object(s)...",
                series_states=series_states
        ):

            modified = False

            for obj_name in obj_names:
                
                if obj_name in section.contours:

                    traces = section.contours[obj_name].getTraces()
                    copy_name = f"{obj_name}_copy"
                    
                    for trace in traces:

                        copy_trace = trace.copy()
                        copy_trace.name = copy_name
                        section.addTrace(copy_trace, log_event=False)

                    modified = True

            if modified:
                section.save()

        ## Assign object attrs to copies
        for obj_name in obj_names:
            self.objects.copyObjAttrs(obj_name, f"{obj_name}_copy")

        self.modified = True

        return [f"{obj}_copy" for obj in obj_names]
    
    def deleteAllTraces(self, trace_name : str, tags : set = None, series_states=None):
        """Delete all traces with a certain name and tag set.
        
            Params:
                trace_name (str): the name of the traces to delete
                tags (set): the tags to check to delete
        """
        for snum, section in self.enumerateSections(
            message="Deleting trace(s)...",
            series_states=series_states
        ):
            if trace_name in section.contours:
                contour = section.contours[trace_name]
                to_del = []
                for trace in contour:
                    if (
                        (tags is not None and trace.tags == tags) or
                        (tags is None)
                    ):
                        to_del.append(trace)
                for trace in to_del:
                    section.removeTrace(trace)
                if to_del:
                    section.save()
        self.modified = True
    
    def editObjectAttributes(
            self, 
            obj_names : list, 
            name : str = None, 
            color : tuple = None, 
            tags : set = None, 
            mode : tuple = None, 
            sections : list = None, 
            series_states=None,
            log_event=True):
        """Edit the attributes of objects.
        
            Params:
                obj_names (list): the names of the objects to rename
                name (str): the new name for the objects
                color (tuple): the new color for the objects
                tags (set): the tags to ADD to the traces of the objects
                mode (tuple): the display mode to set for the traces
                section (list): the section numbers to modify the object on (default: all)
                series_states: the series states as store in the GUI
                log_event (bool): True if event should be logged
        """
        ## Preemptively create log
        if log_event:
            for obj_name in obj_names:
                if name and obj_name != name:
                    self.addLog(obj_name, None, f"Rename object to {name}")
                    self.addLog(name, None, f"Create trace(s) from {obj_name}")
                else:
                    self.addLog(obj_name, None, "Modify object")
        
        ## Modify object on every section
        attrs_migrated = False
        for snum, section in self.enumerateSections(
            message="Modifying object(s)...",
            series_states=series_states
        ):

            ## Move object attrs

            ## Note why this must be done once inside the loop: the loop
            ## initiates series_state data collection, and renaming must happen
            ## after the series state collection; however, it must also happen
            ## before the object is fully deleted.
            
            if name and not attrs_migrated:
                
                for obj_name in obj_names:

                    if obj_name != name:
                        self.renameObjAttrs(obj_name, name)
                        
                attrs_migrated = True
            
            if snum not in sections:  # skip sections that are not included
                continue

            traces = []
            
            for obj_name in obj_names:
                
                if obj_name in section.contours:
                    traces += section.contours[obj_name].getTraces()
                    
            if traces:
                
                section.editTraceAttributes(
                    traces, name, color, tags, mode, add_tags=True, log_event=False
                )
                
                ## Gather new traces
                if name:
                    traces = section.contours[name].getTraces()
                    
                else:
                    traces = []
                    for obj_name in obj_names:
                        if obj_name in section.contours:
                            traces += section.contours[obj_name].getTraces()
                            
                section.save()
        
        self.modified = True

    def smoothObject(self, obj_names: list, series_states=None, log_event=True) -> None:
        """Smooth all traces belonging to an object."""

        window = self.getOption("roll_window")
        
        if log_event:

            for obj_name in obj_names:

                self.addLog(obj_name, None, f"Smooth {obj_name} traces")

        for _, section in self.enumerateSections(
                message="Smoothing traces...",
                series_states=series_states
        ):
            
            for obj_name in obj_names:
                
                obj = section.contours.get(obj_name)
                
                if obj:
                    
                    section.modified_contours.add(obj_name)
                    for trace in obj.traces:
                        trace.smooth(window=window, spacing=0.004)

            section.save()

            self.modified = True
    
    def editObjectRadius(self, obj_names : list, new_rad : float, series_states=None):
        """Change the radii of all traces of an object.
        
            Params:
                obj_names (list): the names of objects to modify
                new_rad (float): the new radius for the traces of the object
                series_states (dict): optional dict for GUI undo states
        """
        for snum, section in self.enumerateSections(
            message="Modifying radii...",
            series_states=series_states
        ):
            traces = []
            for name in obj_names:
                if name in section.contours:
                    traces += section.contours[name].getTraces()
            if traces:
                section.editTraceRadius(traces, new_rad)
                section.save()
        
        self.modified = True
    
    def editObjectShape(self, obj_names : list, new_shape : list, series_states=None):
        """Change the shape of all traces of an object.
        
            Params:
                obj_names (list): the names of objects to modify
                new_shape (list): the new shape for the traces of the object
                series_states (dict): optional dict for GUI undo states
        """
        for snum, section in self.enumerateSections(
            message="Modifying shapes...",
            series_states=series_states
        ):
            traces = []
            for name in obj_names:
                if name in section.contours:
                    traces += section.contours[name].getTraces()
            if traces:
                section.editTraceShape(traces, new_shape)
                section.save()
        
        self.modified = True
    
    def listObjects(self):
        """List all objects in a series."""

        series_data = self.data.data
        objs = list(series_data["objects"].keys())
        objs.sort()

        return objs

    def removeAllTraceTags(self, obj_names : list, series_states=None, log_event=True):
        """Remove all tags from all traces on a set of objects.
        
            Params:
                obj_names (list): a list of object names
                series_states (dict): optional dict for GUI undo states
                log_event (bool): True if event should be logged
        """
        for snum, section in self.enumerateSections(
            message="Removing trace tags...",
            series_states=series_states
        ):
            traces = []
            for obj_name in obj_names:
                if obj_name in section.contours:
                    traces += section.contours[obj_name].getTraces()
            if traces:
                section.editTraceAttributes(
                    traces,
                    name=None,
                    color=None,
                    tags=set(),
                    mode=None, 
                    log_event=False
                )
                section.save()
        
        if log_event:
            for name in obj_names:
                self.addLog(name, None, "Remove all trace tags")

        self.modified = True
    
    def hideObjects(self, obj_names : list, hide=True, series_states=None, log_event=True):
        """Hide all traces of a set of objects throughout the series.
        
            Params:
                obj_names (list): the names of objects to hide
                hide (bool): True if object should be hidden
                series_states (dict): optional dict for GUI undo states
                log_event (bool): True if event should be logged
        """
        for snum, section in self.enumerateSections(
            message="Hiding object(s)..." if hide else "Unhiding object(s)...",
            series_states=series_states
        ):
            modified = False
            for name in obj_names:
                if name in section.contours:
                    contour = section.contours[name]
                    for trace in contour:
                        trace.setHidden(hide)
                        modified = True
                    section.modified_contours.add(name)
            if modified:
                section.save()
        
        if log_event:
            for name in obj_names:
                event = f"{'Hide' if hide else 'Unhide'} object"
                self.addLog(name, None, event)
        
        self.modified = True
    
    def hideAllTraces(self, hidden=True, series_states=None, log_event=True):
        """Hide all traces in the entire series.
        
            Params:
                hidden (bool): True if traces are to be hidden
                series_states (dict): optional dict for GUI undo states
                log_event (bool): True if event should be logged
        """
        for snum, section in self.enumerateSections(
            message="Hiding traces..." if hidden else "Unhiding traces...",
            series_states=series_states
        ):
            for trace in section.tracesAsList():
                trace.setHidden(hidden)
            for name in section.contours:
                section.modified_contours.add(name)
            section.save()
        
        if log_event:
            self.addLog(None, None, f"{'Hide' if hidden else 'Unhide'} all traces in series")
    
    def importObjectGroups(self, other, regex_filters=[], group_filters=[]):
        """Import the object groups from another series.
        
            Params:
                other (Series): the other series
                regex_filters (list): the regex filters for the objects to include
        """
        self.object_groups.merge(other.object_groups, regex_filters, group_filters)
    
    def importZtraceGroups(self, other, regex_filters=[]):
        """Import the ztrace groups from another series.
        
            Params:
                other (Series): the other series
                regex_filters (list): the regex filters for the ztraces to include
        """
        self.ztrace_groups.merge(other.ztrace_groups, regex_filters)
    
    def importHostTree(self, other, regex_filters=[], restrict_to=[]):
        """Import the host tree from another series.
        
            Params:
                other (Series): the other series
                regex_filters (list): regex filters for objects
                group_filters (list): group filters for objects
        """
            
        self.host_tree.merge(other.host_tree, regex_filters, restrict_to)
    
    def importUserCols(self, other, regex_filters=[], restrict_to=[]):
        """Import user columns."""
        # import the user columns
        merged_user_columns = updateDictLists(
            self.user_columns,
            other.user_columns
        )
        if self.user_columns != merged_user_columns:
            self.user_columns = merged_user_columns

        # import the user column object attributes
        for obj_name, obj_data in other.obj_attrs.items():

            if restrict_to and obj_name not in restrict_to:
                continue
            
            if obj_name not in self.data["objects"]:
                continue

            # check regex filters
            passes_filters = False if regex_filters else True
            for rf in regex_filters:
                if bool(re.fullmatch(rf, obj_name)):
                    passes_filters = True
            if not passes_filters:
                continue

            if "user_columns" in obj_data:
                other_uc = obj_data["user_columns"]
                if obj_name not in self.obj_attrs:
                    self.obj_attrs[obj_name] = {}
                if "user_columns" not in self.obj_attrs[obj_name]:
                    self.obj_attrs[obj_name]["user_columns"] = {}
                self_uc = self.obj_attrs[obj_name]["user_columns"]

                for name, value in other_uc.items():
                    if name not in self_uc:
                        ## if the current series has a user_column setting already, do not override it
                        ## is there a better way to handle this?
                        self_uc[name] = value
    
    def importObjAttrs(self, other, regex_filters=[], restrict_to=[]):
        """Import the object attributes from another series.
        
            Params:
                other (Series): the other series
                regex_filters (list): the regex filters for the objects to include
        """

        for obj_name, obj_data in other.obj_attrs.items():

            if restrict_to and obj_name not in restrict_to:
                continue
            
            if obj_name not in self.data["objects"]:
                continue

            # check regex filters
            passes_filters = False if regex_filters else True
            for rf in regex_filters:
                if bool(re.fullmatch(rf, obj_name)):
                    passes_filters = True
            if not passes_filters:
                continue

            for attr_name, attr_value in obj_data.items():
                # skip user column data
                if attr_name == "user_columns":
                    continue

                if obj_name not in self.obj_attrs:
                    self.obj_attrs[obj_name] = {}
                
                if attr_name not in self.obj_attrs[obj_name]:
                    self.obj_attrs[obj_name][attr_name] = attr_value
                # special case: overwrite self curation if other is more recent
                elif attr_name == "curation":
                    self_date = self.obj_attrs[obj_name]["curation"][-1]
                    other_date = attr_value[-1]
                    if other_date >= self_date:
                        self.obj_attrs[obj_name]["curation"] = attr_value
    
    def importTraces(
            self,
            other, 
            srange : tuple = None, 
            regex_filters : list = [],
            group_filters : list = [],
            threshold : float = 0.95, 
            flag_conflicts : bool = True,
            check_history : bool = True,
            import_obj_attrs : bool = True,
            keep_above : str = "self",
            keep_below : str = "",
            series_states=None,
            log_event=True):
        """Import all the traces from another series.
        
            Params:
                other (Series): the series to import from
                srange (tuple): the range of sections to include in import (exclusive)
                regex_filters (list): regex filters for objects
                group_filters (list): group filters for objects
                threshold (float): the overlap threshold
                remove_old_overlaps (bool): True if old traces overlapping new traces should be removed
                flag_conflicts (bool): True if conflicts should be flagged
                check_history (bool): True if history should be checked
                import_obj_attrs (bool): True if object attributes should all be imported
                keep_above (str): the series that is favored for functional duplicates (above the overlap threshold; "self", "other", or "")
                keep_below (str): the series that is favored in the case of a conflict (overlap not reaching the threshold; "self", "other", or "")
                series_states (dict): optional dict of undo states for GUI
                log_event (bool): True if event should be logged
        """
        # # ensure that the two series have the same sections
        # if sorted(list(self.sections.keys())) != sorted(list(other.sections.keys())):
        #     return
        
        ## Supress logging for object creation
        self.data.supress_logging = True

        ## Get current date and time for tagging
        d, t = getDateTime()
        dt_str = d + "-" + t
        
        histories = LogSetPair(
            self.getFullHistory(),
            other.getFullHistory()
        )
        
        for snum, section in self.enumerateSections(
            message="Importing traces...",
            series_states=series_states
        ):
            ## Skip if section not requested or does not exist in other series
            skip = snum not in range(*srange) or snum not in other.sections
            
            if skip: 
                continue
            
            o_section = other.loadSection(snum)  # other section
            histories_param = histories if check_history else None  # skip history if checking is not requested

            section.importTraces(
                o_section,
                regex_filters,
                group_filters,
                threshold,
                flag_conflicts,
                histories_param,
                keep_above,
                keep_below,
                dt_str
            )
        
        ## Un-supress logging for object creation
        self.data.supress_logging = False

        ## Restrict object if with group filters
        restrict_to = []  # empty = no additional restrictions
        
        if group_filters:

            other_groups = other.object_groups.getGroupDict()
            
            for gf in group_filters:
                restrict_to += other_groups[gf]

        ## Import ALL object attributes
        if import_obj_attrs:
            
            self.importObjectGroups(other, regex_filters, group_filters)
            self.importHostTree(other, regex_filters, restrict_to)
            self.importObjAttrs(other, regex_filters, restrict_to)
            self.importUserCols(other, regex_filters, restrict_to)

        ## Import history
        if log_event:
            
            self.addLog(None, None, "Begin importing traces from another series")

            histories.importLogs(
                self,
                traces=True,
                ztraces=False,
                srange=srange,
                regex_filters=regex_filters
            )
            
            self.addLog(None, None, "Finish importing traces from another series")
        
        self.save()
    
    def importZtraces(self, other, regex_filters : list = [], import_attrs : bool = True, series_states=None, log_event=True):
        """Import all the ztraces from another series.
        
            Params:
                other (Series): the series to import from
                regex_filters (list): the filters for the objects to import
                import_attrs (bool): True if ztrace attrs (groups) should be imported
                series_states (SeriesStates): the series undo states from the GUI
                log_event (bool): True if event should be logged
        """
        if series_states:
            series_states.addState()
        
        # gather the mismatched calibrations
        cal_conversions = {}
        for snum in self.sections:
            if snum not in other.sections:
                continue
            s_mag = self.data["sections"][snum]["mag"]
            o_mag = other.data["sections"][snum]["mag"]
            if abs(o_mag - s_mag) > 1e-8:
                cal_conversions[snum] = (o_mag, s_mag)

        
        for o_zname, o_ztrace in other.ztraces.items():
            passes_filters = False if regex_filters else True
            for rf in regex_filters:
                if bool(re.fullmatch(rf, o_zname)):
                    passes_filters = True
            if not passes_filters:
                continue

            # check to ensure all sections included
            sections_check = True
            for x, y, snum in o_ztrace.points:
                if snum not in self.sections:
                    sections_check = False
                    break
            if not sections_check:
                print(f"Skipping {o_zname}: includes sections not in this series.")
                continue

            # modify the ztrace scaling if necessary
            for snum, (o_mag, s_mag) in cal_conversions.items():
                o_ztrace.magScale(snum, o_mag, s_mag)

            # do not replace existing ztraces
            if o_zname not in self.ztraces:
                self.ztraces[o_zname] = o_ztrace.copy()
            # add a new ztrace if same name but dont overlap
            elif not self.ztraces[o_zname].overlaps(o_ztrace):
                n = 1
                while (f"{o_zname}-imported-{n}") in self.ztraces:
                    n += 1
                self.ztraces[f"{o_zname}-imported-{n}"] = o_ztrace.copy()
        
        # import the group data
        if import_attrs:
            self.importZtraceGroups(other, regex_filters)
        
        if log_event:
            # import the history
            histories = LogSetPair(
                self.getFullHistory(),
                other.getFullHistory()
            )
            self.addLog(None, None, "Begin importing ztraces from another series")
            histories.importLogs(
                self,
                traces=False,
                ztraces=True,
                regex_filters=regex_filters
            )
            self.addLog(None, None, "Finish importing ztraces from another series")
        
        self.save()
    
    def importTransforms(self, other, import_as : list, series_states=None, log_event=True):
        """Import transforms from another series.
        
            Params:
                other (series): the series to import transforms from
                import_as (list): the list of (alignment to import, name for alignment in current series)
                series_states (dict): optiona dict of undo states for GUI
                log_event (bool): True if the event should be logged
        """
        for s_snum, s_section in self.enumerateSections(message="Importing alignments..."):
            if s_snum in other.sections:
                o_section = other.loadSection(s_snum)
                mags_match = abs(o_section.mag - s_section.mag) <= 1e-8
                for alignment, new_name in import_as:
                    if not mags_match:
                        o_section.tforms[alignment].magScale(o_section.mag, s_section.mag)
                    s_section.tforms[new_name] = o_section.tforms[alignment].copy()
            else:  # write blank if section not in other series
                for alignment, new_name in import_as:
                    s_section.tforms[new_name] = Transform.identity()
            s_section.save()

        if log_event:
            alignments_str = " ".join(a[0] for a in import_as)
            self.addLog(None, None, f"Import alignments {alignments_str} from another series")

        self.save()
    
    def importBC(self, other, import_as : list, log_event=True):
        """Import brightness/contrast profiles from another series.
        
            Params:
                other (series): the series to import transforms from
                import_as (list): the list of (profile to import, name for profile in current series)
                log_event (bool): True if the event should be logged
        """
        for s_snum, s_section in self.enumerateSections(message="Importing brightness/contrast profiles..."):
            if s_snum in other.sections:
                o_section = other.loadSection(s_snum)
                for profile, new_name in import_as:
                    s_section.bc_profiles[new_name] = o_section.bc_profiles[profile].copy()
            else:  # write blank b/c if section not in other series
                for profile, new_name in import_as:
                    s_section.bc_profiles[new_name] = (0, 0)
            s_section.save()

        if log_event:
            profiles_str = " ".join(p[0] for p in import_as)
            self.addLog(None, None, f"Import brightness-contrast profiles {profiles_str} from another series")

        self.save()
    
    def importPalettes(self, other, import_as, log_event=True):
        """Import the palettes from another series.
        
            Params:
                other (Series): the series to import from
                import_as (list): the list of (palette to import, name for palette in current series)
                log_event (bool): True if event should be logged
        """
        for palette, new_name in import_as:
            trace_list = other.palette_traces[palette]
            self.palette_traces[new_name] = trace_list.copy()
        
        if log_event:
            palettes_str = " ".join(p[0] for p in import_as)
            self.addLog(None, None, f"Import palettes {palettes_str} from another series")
        
        self.save()
    
    def importFlags(self, other, srange, series_states=None, log_event=True):
        """Import flags from another series.
        
            Params:
                other (Series): the series to import from
                srange (tuple): the range of sections to import from
                series_states (SeriesStates): the series undo states from the GUI
                log_event (bool): True if event should be logged
        """
        for snum, section in self.enumerateSections(
            message="Importing flags...",
            series_states=series_states
        ):
            if snum not in other.sections:  # skip if section does not exist in other series
                continue
            if snum not in range(*srange):  # skip if not in requested section range
                continue

            new_flag_pool = section.flags.copy()
            o_section = other.loadSection(snum)  # sending section
            mags_match = abs(o_section.mag - section.mag) <= 1e-8

            for o_flag in o_section.flags:
                # adjust the flag to match magnification if necessary
                if not mags_match:
                    o_flag.magScale(o_section.mag, section.mag)
                eq_found = False
                for s_flag in section.flags:
                    if s_flag.equals(o_flag):
                        eq_found = True
                        # if two of the same found, use one with more comments
                        # otherwise, just keep the self flag
                        slen = len(s_flag.comments)
                        olen = len(o_flag.comments)
                        if olen > slen:
                            new_flag_pool.append(o_flag)
                            new_flag_pool.remove(s_flag)
                            section.flags_modified = True
                        break
                if not eq_found:
                    new_flag_pool.append(o_flag)
                    section.flags_modified = True

            if section.flags_modified:
                section.flags = new_flag_pool
                section.save()
        
        if log_event:
            self.addLog(None, None, "Import flags from another series")

    @staticmethod
    def getDefaultPaletteTraces() -> list:
        """Return the default palette trace list.
        
            Returns:
                (list): the list of the default palette traces
        """
        palette_traces = []
        for l in default_traces:
            palette_traces.append(Trace.fromList(l.copy()))
        return palette_traces * 2
    
    def getRecentSegGroup(self) -> str:
        """Return the most recent segmentation group name.
        
            Returns:
                (str): the name of the most recent segmentation group
        """
        g = None
        for group in self.object_groups.getGroupList():
            if group.startswith("seg_") and (
                g is None or group > g
            ):
                g = group
        return g
    
    def deleteDuplicateTraces(self, threshold : float, include_locked=False, series_states=None, log_event=True):
        """Delete all duplicate traces in the series (keep tags).
        
            Params:
                threshold (float): the threshold for overlapping traces to be considered duplicates
                series_states (dict): optional dict of undo states for GUI
                log_event (bool): True if event should be logged
        """
        removed = {}
        for snum, section in self.enumerateSections(
            message="Removing duplicate traces...",
            series_states=series_states
        ):
            found_on_section = False
            for cname in section.contours:
                if not include_locked and self.getAttr(cname, "locked"):
                    continue
                i = 1
                while i < len(section.contours[cname]):
                    trace1 = section.contours[cname][i]
                    # check against all previous traces
                    for j in range(i-1, -1, -1):
                        trace2 = section.contours[cname][j]
                        # if overlaps, remove trace and break
                        if trace1.overlaps(trace2, threshold=threshold):
                            if snum not in removed:
                                removed[snum] = set()
                            removed[snum].add(cname)
                            found_on_section = True
                            trace1.mergeTags(trace2)
                            section.removeTrace(trace2)
                            i -= 1
                            break
                    i += 1
            if found_on_section:
                section.save()
        
        if log_event:
            self.addLog(None, None, "Delete all duplicate traces")

        return removed

    def addLog(self, obj_name : str, snum : int, event : str):
        """Add a log to the log set.
        
            Params:
                obj_name (str): the name of the modified object
                snum (int): the section number of the event
                event (str): the description of the event
        """
        self.log_set.addLog(self.user, obj_name, snum, event)

        # update the user data
        if obj_name:
            self.setAttr(obj_name, "last_user", self.user)
            self.editors.add(self.user)
    
    def getFullHistory(self) -> LogSet:
        """Get all the logs for the series.
        
            Returns:
                (LogSet): the object containing the full history
        """
        csv_fp = os.path.join(self.hidden_dir, "existing_log.csv")
        with open(csv_fp, "r") as f:
            log_list = f.readlines()[1:]
        full_hist = LogSet.fromList(log_list)
        for log in self.log_set.all_logs:
            full_hist.addExistingLog(log)
        
        return full_hist

    def setCuration(self, names : list, cr_status : str, assign_to : str = ""):
        """Set the curation status for a set of objects.
        
            Params:
                names (list): the object names to mark as curated
                cr_status(str): the curation state to set
                asign_to (str): the user to assign to if Needs Curation
        """
        for name in names:
            if cr_status == "":
                self.setAttr(name, "curation", None)
                self.log_set.removeCuration(name)
            elif cr_status == "Needs curation":
                self.setAttr(name, "curation", (False, assign_to, getDateTime()[0]))
                self.addLog(name, None, "Mark as needs curation")
            elif cr_status == "Curated":
                self.setAttr(name, "curation", (True, self.user, getDateTime()[0]))
                self.addLog(name, None, "Mark as curated")
    
    def reorderSections(self, d : dict = None, log_event=True):
        """Reorder the sections.
        
            Params:
                d (dict): old_snum : new_snum for every section
                log_event (bool): True if event should be logged
        """
        if not d:
            d = dict(tuple((snum, i) for i, snum in enumerate(self.sections.keys())))
        
        # rename the section files
        for old_snum, new_snum in d.items():
            os.rename(
                os.path.join(self.hidden_dir, f"{self.name}.{old_snum}"),
                os.path.join(self.hidden_dir, f"{self.name}.{new_snum}.temp")
            )
        # remove temp ext
        for f in os.listdir(self.hidden_dir):
            if f.endswith(".temp"):
                updated_f = f[:-len(".temp")]
                os.rename(
                    os.path.join(self.hidden_dir, f),
                    os.path.join(self.hidden_dir, updated_f)
                )
        
        # update the ztraces
        for ztrace in self.ztraces.values():
            pts = []
            for pt in ztrace.points:
                pts.append((pt[0], pt[1], d[pt[2]]))
            ztrace.points = pts
                
        # create the new sections dict
        self.sections = {}
        for snum in sorted(d.values()):
            self.sections[snum] = f"{self.name}.{snum}"

        self.current_section = d[self.current_section]

        if log_event:
            self.addLog(None, None, "Reorder sections")
    
    def insertSection(self, index : int, src : str, mag : float, thickness : float, log_event=True):
        """Create a new section.
        
            Params:
                index (int): the index of the new section
                src (str): the path to the image for the new section
                mag (float): the mag of the new section
                thickness (float): the thickness of the new section
                log_event (bool): True if event should be logged
        """
        # create the new section object
        max_snum = max(self.sections.keys()) + 1
        Section.new(
            self.name,
            max_snum,
            src,
            mag,
            thickness,
            self.hidden_dir
        )
        self.sections[max_snum] = f"{self.name}.{max_snum}"

        # reorder the sections
        if index in self.sections:
            reorder = dict(
                (n, n + 1 if n >= index else n) for n in self.sections
            )
        else:
            reorder = dict((n, n) for n in self.sections)
        reorder[max_snum] = index
        self.reorderSections(reorder, log_event=False)

        if log_event:
            self.addLog(None, None, "Insert section")
    
    def getAttr(self, name : str, attr_name : str, ztrace=False):
        """Get the attributes for an object in the series.
        
            Params:
                obj_name (str): the name of the object
                attr_name (str): the name of the attribute to get
            Returns:
                the request attribute
        """
        if ztrace:
            attrs = self.ztrace_attrs
        else:
            attrs = self.obj_attrs
        
        if not name in attrs or attr_name not in attrs[name]:
            # return defaults if not set
            if attr_name == "3D_mode":
                return "surface"
            if attr_name == "3D_opacity":
                return 1
            elif attr_name == "last_user":
                return ""
            elif attr_name == "curation":
                return None
            elif attr_name == "comment":
                return ""
            elif attr_name == "alignment":
                return None
            elif attr_name == "locked":
                return False
            elif attr_name == "user_columns":
                return {}
            else:
                return
        else:
            return attrs[name][attr_name]
    
    def setAttr(self, name : str, attr_name : str, value, ztrace=False):
        """Set the attributes for an object in the series.
        
            Params:
                obj_name (str): the name of the object
                attr_name (str): the name of the attribute to set
                value: the value to set for the attributes
        """
        if ztrace:
            attrs = self.ztrace_attrs
        else:
            attrs = self.obj_attrs
        
        if name not in attrs:
            attrs[name] = {}
        attrs[name][attr_name] = value
        if value is None:
            del(attrs[name][attr_name])
            if not attrs[name]:
                del(attrs[name])
    
    def removeObjAttrs(self, name : str):
        """Delete all attrs associated with an object name.

        (Automatically called when object is deleted.)
        
            Params:
                name (str): the name of the object
        """
        # object groups
        self.object_groups.removeObject(name)

        # obj_attrs
        del(self.obj_attrs[name])

        # object host
        self.host_tree.removeObject(name)

    def renameObjAttrs(self, old_name, new_name):
        """Change the attibutes for an object that was renamed.

        (Automatically called when object is renamed.)
        
            Params:
                old_name (str): the original name of the object
                new_name (str): the new name for the object
        """
        # if new_name in self.data["objects"]:
        #     return  # do not overwrite if object exists
        
        # object groups
        groups = self.object_groups.getObjectGroups(old_name)
        for group in groups:
            self.object_groups.add(group, new_name)
        
        # import the object attributes
        if old_name in self.obj_attrs:
            if new_name not in self.obj_attrs:
                self.obj_attrs[new_name] = {}

            # find non-existing attributes and import them in
            old_attrs = self.obj_attrs[old_name]
            new_attrs = self.obj_attrs[new_name]
            for attr, value in old_attrs.items():
                if attr not in new_attrs:
                    new_attrs[attr] = value
            
            # find non-existing user columns and import them in
            if "user_columns" in old_attrs:
                if "user_columns" not in new_attrs:
                    new_attrs["user_columns"] = {}
                old_cols = old_attrs["user_columns"]
                new_cols = new_attrs["user_columns"]
                for col_name, opt in old_cols.items():
                    if col_name not in new_cols:
                        new_cols[col_name] = opt

            self.obj_attrs[new_name] = self.obj_attrs[old_name].copy()
        
        # rename obj hosts
        self.host_tree.renameObject(old_name, new_name)
    
    def getAlignments(self) -> list:
        """Return a list of alignment names."""
        snum = list(self.sections.keys())[0]  # grab valid section number
        sec_data = self.data["sections"]
        anames = list(sec_data[snum]["tforms"].keys())
        return anames

    def updateCurationFromHistory(self):
        """Update curation status of all objects from the history."""
        full_hist = self.getFullHistory().all_logs

        marked_objs = set()
        for log in reversed(full_hist):
            name = log.obj_name
            if not name or name in marked_objs:
                continue

            if "Mark as curated" in log.event:
                if name not in self.obj_attrs:
                    self.obj_attrs[name] = {}
                if "curation" not in self.obj_attrs[name] or not self.obj_attrs[name]["curation"][0]:  # overwrite if at previous step in curation flow
                    self.obj_attrs[name]["curation"] = (True, log.user, log.date)
                marked_objs.add(name)
            elif "Mark as needs curation" in log.event:
                if name not in self.obj_attrs:
                    self.obj_attrs[name] = {}
                if "curation" not in self.obj_attrs[name]:
                    self.obj_attrs[name]["curation"] = (False, "", log.date)
                marked_objs.add(name)
    
    def getOption(self, option_name : str, get_default=False):
        """Get an option from the series (or computer)
        
            Params:
                option_name (str): the name of the option
                get_default (bool): True if only default should be returned
        """
        ## Check for internal series option first
        if option_name in self.options:
            
            if get_default:
                opt = Series.getEmptyDict()["options"][option_name]
            else:
                opt = self.options[option_name]
                
            return opt
        
        ## Get sane settings and defaults
        if option_name in Series.qsettings_series_defaults:
            
            if self.isWelcomeSeries():  # return defaults if accessing series setting
                return Series.qsettings_series_defaults[option_name]
            
            settings = QSettings("KHLab", f"PyReconstruct-{self.code}")
            defaults = Series.qsettings_series_defaults
            
        elif option_name in Series.qsettings_defaults:
            
            settings = QSettings("KHLab", "PyReconstruct")
            defaults = Series.qsettings_defaults
            
        else:
            
            return None
        
        ## Get the option
        if get_default:
            return defaults[option_name]
        elif settings.contains(option_name):
            option_type = type(defaults[option_name])
            option = settings.value(
                option_name,
                type=(str if option_type in (dict, list, tuple) else option_type)
            )
            if option_type in (dict, list, tuple):
                option = json.loads(option)
        else:
            option = defaults[option_name]
            self.setOption(option_name, option)
        
        ## CHECKS FOR UPDATES

        ## Check for disallowing laplacian smoothing
        if option_name == "3D_smoothing" and option == "laplacian":
            option = "humphrey"
            self.setOption(option_name, option)

        ## Check for tables
        if "_columns" in option_name:
            if type(option) is not list:
                raise Exception("boo")
        
        return option
                    
    def setOption(self, option_name : str, value):
        """Set an option
        
            Params:
                options_name (str): the name of the option
                value: the value to set the option as
        """
        # check for internal series option first
        if option_name in self.options:
            self.options[option_name] = value
            return
        
        # convert format if necessary
        value_type = type(value)
        if value_type in (dict, list, tuple):
            value = json.dumps(value)
        
        # get the proper settings
        if option_name in Series.qsettings_series_defaults:
            if self.isWelcomeSeries():
                return  # prevent setting for the welcome series
            settings = QSettings("KHLab", f"PyReconstruct-{self.code}")
        elif option_name in Series.qsettings_defaults:
            settings = QSettings("KHLab", "PyReconstruct")
        else:
            return
        
        settings.setValue(option_name, value)
    
    @property
    def user(self):
        return self.getOption("username")

    @user.setter
    def user(self, value):
        self.setOption("username", value)
    
    @property
    def avg_mag(self):
        return self.data.getAvgMag()

    @property
    def avg_thickness(self):
         return self.data.getAvgThickness()

    def exportTracePaletteCSV(self, fp : str, palette_name : str = None):
        """Export the trace palette as a CSV file.
        
            Params:
                fp (str): the filepath for the CSV file
                palette_name (str): the name of the palette to export (default: current palette)
        """
        if palette_name is None:
            palette_name = self.palette_index[0]
        
        traces = self.palette_traces[palette_name].copy()
        csv_str = "Name,Color,Fill,Tags,X,Y\n"

        for trace in traces:
            trace : Trace
            name = trace.name
            color = " ".join(str(n) for n in trace.color)
            fill = " ".join(trace.fill_mode)
            tags = " ".join(trace.tags)
            x = " ".join(str(x) for x, y in trace.points)
            y = " ".join(str(y) for x, y in trace.points)
            csv_str += ",".join([name, color, fill, tags, x, y]) + "\n"
        
        with open(fp, "w") as f:
            f.write(csv_str)
    
    def importTracePaletteCSV(self, fp : str, palette_name : str = None):
        """Import the trace palette from a CSV file.
        
            Params:
                fp (str): the path to the CSV file
                palette_name (str): the name for the new palette (default: overwrite current)
        """
        if palette_name is None:
            palette_name = self.palette_index[0]
        
        with open(fp, "r") as f:
            lines = f.readlines()[1:]
        
        trace_list = []

        for line in lines:
            l = line.split(",")
            name = l[0]
            color = tuple(int(n) for n in l[1].split())
            fill = tuple(l[2].split())
            tags = set(l[3].split())
            x = [float(n) for n in l[4].split()]
            y = [float(n) for n in l[5].split()]

            t = Trace(name, color)
            t.fill_mode = fill
            t.tags = tags
            t.points = list(zip(x, y))
            trace_list.append(t)
        
        self.palette_traces[palette_name] = trace_list

    def exportObjectsCSV(self, output_fp: Union[str, Path]="", notify: bool=False) -> None:
        """Export all object data as CSV file."""

        self.objects.exportCSV(str(output_fp))

        if notify:

            print(f"CSV exported to: {str(output_fp)}")

    def exportZtracesCSV(self, output_fp: Union[str, Path]="", notify:bool=False) -> None:
        """Export all z-trace data as CSV file."""

        sep = "|"

        out_str = f"series{sep}ztrace{sep}start{sep}end{sep}length\n"

        for _, z in self.ztraces.items():

            start = z.getStart()
            end = z.getEnd()
            z_len = round(z.getDistance(self), 5)
            
            out_str += f"{self.code}{sep}{z.name}{sep}{start}{sep}{end}{sep}{z_len}\n"

        if output_fp:

            with open(str(output_fp), "w") as f:
                f.write(out_str)

        if notify:

            print(f"CSV exported to {str(output_fp)}")

    def getEditorsFromHistory(self):
        """Get the set of editors from the history of the series."""
        editors = set()
        try:
            ls = self.getFullHistory()
        except:
            print("ERROR: corrupt history. Skipping editors update...")
            return set()
        for l in ls.all_logs:
            if l.user:
                editors.add(l.user)
        return editors

    def getBackupPath(self, comment : str = "", check_existing : bool = True):
        """Get the file path for a backup file for this series.
        
            Params:
                comment (str): an optional comment to add to the end of the filename.
                check_existing (bool): check for existing file and append numbers if exists
        """
        fname_list = []

        if self.getOption("backup_prefix"):
            s = self.getOption("backup_prefix_str")
            if s: fname_list.append(s)

        if self.getOption("backup_series"):
            fname_list.append(self.code)

        if self.getOption("backup_filename"):
            fname_list.append(self.name)
        
        now = datetime.utcnow() if self.getOption("utc") else datetime.now()

        if self.getOption("backup_date"):
            date = now.strftime(self.getOption("backup_date_str"))
            fname_list.append(date)
        
        if self.getOption("backup_time"):
            time = now.strftime(self.getOption("backup_time_str"))
            fname_list.append(time)
        
        if self.getOption("backup_user"):
            fname_list.append(self.user)

        if self.getOption("backup_suffix"):
            s = self.getOption("backup_suffix_str")
            if s: fname_list.append(s)
        
        if comment:
            fname_list.append(comment)
        
        dl = self.getOption("backup_delimiter")
        fname_list = [s.strip() for s in fname_list]
        fname = dl.join(fname_list)
        fname = dl.join(fname.split())

        folder = self.getOption("backup_dir")
        fp = os.path.join(folder, fname)

        if check_existing and os.path.isfile(f"{fp}.jser"):
            n = 1
            while os.path.isfile(f"{fp}-{n:02d}.jser"):
                n += 1
            fp = f"{fp}-{n:02d}.jser"
        else:
            fp += ".jser"

        return fp
    
    def addUserCol(self, col_name : str, opts : list, log_event=True):
        """Add a user-defined column to the series.
        
            Params:
                col_name (str): the name of the column to add
                opts (list): the possible strings to put into the column
        """
        col_name = col_name.replace(" ", "_")
        for i, opt in enumerate(opts):
            opts[i] = opt.replace(" ", "_")
        
        # refuse to add if already exists
        if col_name in self.user_columns:
            return
        
        self.user_columns[col_name] = opts
        
        if log_event:
            self.addLog(None, None, f"Add user column {col_name}")
    
    def removeUserCol(self, col_name : str, log_event=True):
        """Remove a user-defined column.
        
            Params:
                col_name (str): the name of the column to remove
        """
        if col_name in self.user_columns:
            del(self.user_columns[col_name])

        # iterate through all object attributes and remove the column data
        for attrs in self.obj_attrs.values():
            if "user_columns" in attrs and col_name in attrs["user_columns"]:
                del(attrs["user_columns"][col_name])
        
        if log_event:
            self.addLog(None, None, f"Delete user column {col_name}")
        
    def editUserCol(self, col_name : str, new_name : str, new_opts : list, log_event=True):
        """Edit a user-defined column.
        
            Params:
                col_name (str): the original name of the column
                new_name (str): the new name for the column
                new_opts (list): the new options for the column
        """
        new_name = new_name.replace(" ", "_")
        for i, opt in enumerate(new_opts):
            new_opts[i] = opt.replace(" ", "_")

        # refuse to edit if column does not exist or if new name already exists
        if col_name not in self.user_columns:
            return
        if new_name != col_name and new_name in self.user_columns:
            return
        
        if col_name != new_name:
            # rename the column in the user_columns dict
            self.user_columns[new_name] = self.user_columns[col_name]
            del(self.user_columns[col_name])
            # rename the column in all obj attrs
            for attrs in self.obj_attrs.values():
                if "user_columns" in attrs and col_name in attrs["user_columns"]:
                    attrs["user_columns"][new_name] = attrs["user_columns"][col_name]
                    del(attrs["user_columns"][col_name])
        col_name = new_name

        if self.user_columns[col_name] != new_opts:
            # replace the options in the user_columns dict
            self.user_columns[col_name] = new_opts
            # remove old options from all obj attrs
            for attrs in self.obj_attrs.values():
                if "user_columns" in attrs and col_name in attrs["user_columns"]:
                    if attrs["user_columns"][col_name] not in new_opts:
                        del(attrs["user_columns"][col_name])
        
        if log_event:
            self.addLog(None, None, f"Edit user column {new_name}")
    
    def getUserColAttr(self, obj_name : str, col_name : str):
        """Get the user-defined column attribute of an object.

            Params:
                obj_name (str): the name of the object
                col_name (str): the name of the user-defined column
        """
        column_data = self.getAttr(obj_name, "user_columns")
        if col_name not in column_data:
            return None
        else:
            return column_data[col_name]
    
    def setUserColAttr(self, obj_name : str, col_name : str, value : str):
        """Set the user defined column attribute of an object.
        
            Params:
                obj_name (str): the name of the object
                col_name (str): the column of the object
                value (str): the value to set the object column attribute
        """
        value = value.replace(" ", "_")
        column_data = self.getAttr(obj_name, "user_columns")
        if value:
            column_data[col_name] = value
        elif not value and col_name in column_data:
            del(column_data[col_name])
        self.setAttr(obj_name, "user_columns", column_data)
    
    def exportUserColsText(self, out_fp : str):
        """Export the user columns to a text file."""
        s = ""
        for col_name, opts in self.user_columns.items():
            s += f"{col_name}: {', '.join(opts)}\n"
        with open(out_fp, "w") as f:
            f.write(s)
    
    def importUserColsText(self, fp : str):
        """Import user columns from a text file."""
        # FORMAT:
        # name: option, option, option
        # name: option, option, option
        new_columns = {}
        with open(fp, "r") as f:
            lines = f.readlines()
        for line in lines:
            line = line.strip()
            # skip blank lines:
            if not line:
                continue
            try:
                col_name, opts_str = tuple(line.split(": "))
                col_name = col_name.replace(" ", "_")
                opts = opts_str.split(", ")
                opts = [opt.replace(" ", "_") for opt in opts]
                new_columns[col_name] = opts
            except:
                raise Exception("Incorrect user columns text formatting.")
        
        # update the user columns
        for col_name, opts in new_columns.items():
            if col_name not in self.user_columns:
                self.user_columns[col_name] = opts
    
    def deleteSections(self, section_numbers : list, log_event=True):
        """Delete sections in the series."""
        for snum in section_numbers:
            # delete the file
            filename = self.sections[snum]
            os.remove(os.path.join(self.getwdir(), filename))
            # delete link to file
            del(self.sections[snum])
            if log_event:
                self.addLog(None, snum, "Delete section")
        
        # remove ztrace links to sections
        for ztrace in self.ztraces.values():
            pts = []
            for pt in ztrace.points:
                if pt[2] not in section_numbers:
                    pts.append(pt)
            ztrace.points = pts
    
    def splitObject(self, name : str, series_states=None, log_event=True):
        """Split an object into one object per trace.
        
            Params:
                name (str): the name of the object to split
        """
        n = 1
        digits = len(str(self.data.getCount(name)))
        new_names = set()

        ## Get original obj attrs
        alignment, obj_groups, host = self.objects.getSourceAttrs(name)

        for snum, section in self.enumerateSections(
            message="Splitting object...",
            series_states=series_states
        ):
            if name in section.contours:
                traces = section.contours[name].getTraces()
                for trace in traces:
                    section.removeTrace(trace, log_event=False)
                    trace = trace.copy()
                    trace.name = f"{trace.name}_{n:0{digits}d}"
                    new_names.add(trace.name)  # keep track of all the new object names
                    section.addTrace(trace, log_event=False)
                    n += 1
                section.save()

        ## Assign original attrs to new objects
        for obj in new_names:
            self.objects.assignCopyAttrs(obj, alignment, obj_groups, host)
        
        if log_event:
            self.addLog(name, None, "Split into individual objects per trace")
        
        return new_names

    def setObjHosts(self, obj_names : list, host_names : list):
        """Set the host for object(s).
        
            Params:
                obj_names (list): the names of the objects with hosts to set
                host_name (list): the name of the host to set
        """
        # ensure that hosts exist
        for n in host_names:
            if n not in self.data["objects"]:
                raise Exception("Host object does not exist.")
        
        # check to ensure that objects are not hosts of each other
        for hn in host_names:
            if bool(set(obj_names) & set(self.getObjHosts(hn, traverse=True))):  # if any intersection exists between the two
                raise Exception("Objects cannot be hosts of each other.")

        for obj_name in obj_names:
            self.host_tree.clearHosts(obj_name)
            self.host_tree.add(obj_name, host_names.copy())
    
    def getObjHosts(self, obj_name : str, traverse=False, only_secondary=False):
        """Get the host(s) for an object.
        
            Params:
                obj_name (str): the name of the object to retreive the hosts for
                traverse (bool): True if all hosts should be returned
                only_secondary (bool): True if only secondary hosts should be included in the traverse
        """
        return self.host_tree.getHosts(obj_name, traverse, only_secondary)
    
    def clearObjHosts(self, obj_names : list):
        """Clear the host for object(s).
        
            Params:
                obj_names (list): the names of the objects whose hosts should be cleared
        """
        for obj_name in obj_names:
            self.host_tree.clearHosts(obj_name)
    
    def clearTracking(self):
        """Clear the tracking of modified ztraces and modified objects."""
        self.modified_ztraces = set()
        self.modified_objects = set()

    def initGroupViz(self) -> dict:
        """Get initial group visibility."""

        groups = self.object_groups.getGroupList()

        if not groups:
            
            return {}
        
        else:
            
            return {group: True for group in groups}

    @property
    def alignments(self):
        """Return the possible alignments for the series."""
        section_data_list = list(self.data["sections"].values())
        alignments = set(section_data_list[0]["tforms"].keys())
        for section_data in section_data_list[1:]:
            a = set(section_data["tforms"].keys())
            if alignments != a:
                raise Exception("Sections have differently named alignments.")
        return alignments
    
    @property
    def bc_profiles(self):
        """Return the possible brightness/contrast profiles for the series."""
        section_data_list = list(self.data["sections"].values())
        bc_profiles = set(section_data_list[0]["bc_profiles"].keys())
        for section_data in section_data_list[1:]:
            p = set(section_data["bc_profiles"].keys())
            if bc_profiles != p:
                raise Exception("Sections have differently named brightness/contrast profiles.")
        return bc_profiles

    
class SeriesIterator():

    def __init__(self, series : Series, show_progress : bool, message : str, series_states, breakable=True):
        """Create the series iterator object.
        
            Params:
                series (Series): the series object
                show_progress (bool): show progress dialog if True
                message (str): the message to show
                series_states (dict): section number : SectionStates (for use with GUI)
                breakable (bool): True if series state is breakable
        """
        self.series = series
        self.section = None
        self.show_progress = show_progress
        self.message = message
        self.series_states = series_states
        if self.series_states is not None:
            self.series_states.addState(breakable)
    
    def __iter__(self):
        """Allow the user to iterate through the sections."""
        self.section_numbers = sorted(list(self.series.sections.keys()))
        self.sni = 0
        if self.show_progress:
            self.progbar = getProgbar(
                text=self.message,
                cancel=False
            )
        return self
    
    def __next__(self):
        """Return the next section."""
        # update the series states of the previous section if requested
        if self.series_states and self.section and (
            self.section.getAllModifiedNames() or 
            self.section.tformsModified() or
            self.section.flags_modified
        ):
            self.series_states[self.section.n].addState(
                self.section, self.series
            )
            self.series_states.addSectionUndo(self.section.n)

        if self.sni < len(self.section_numbers):
            if self.show_progress:
                    self.progbar.setValue(self.sni / len(self.section_numbers) * 100)
            snum = self.section_numbers[self.sni]
            self.section = self.series.loadSection(snum)
            self.sni += 1

            # check if states have been initialized
            if self.series_states:
                self.series_states[self.section]
            
            return snum, self.section
        
        else:
            if self.show_progress:
                self.progbar.setValue(self.sni / len(self.section_numbers) * 100)
            raise StopIteration


def updateDictLists(d1 : dict, d2 : dict):
    """In the cases where two dictionaries have values as lists, combine the two lists for each value."""
    d = deepcopy(d1)
    for k, l in d2.items():
        if k not in d:
            d[k] = []
        d[k] += l
        d[k] = list(set(l))  # remove redundant values
    return d
