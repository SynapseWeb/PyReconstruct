import os
import json
import shutil
from datetime import datetime

from .ztrace import Ztrace
from .section import Section
from .contour import Contour
from .trace import Trace
from .transform import Transform
from .obj_group_dict import ObjGroupDict
from .object_table_item import ObjectTableItem

from modules.constants import (
    createHiddenDir,
    assets_dir,
    welcome_series_dir
)

from modules.calc import mergeTraces

from modules.constants import welcome_series_dir

try:
    from modules.gui.utils import progbar
    prog_imported = True
except ImportError:
    prog_imported = False

from modules.backend.threading import ThreadPool

default_traces = [
    ['circle', [-0.0948664, -0.0948664, -0.0316285, 0.0316285, 0.0948664, 0.0948664, 0.0316285, -0.0316285], [0.0316285, -0.0316285, -0.0948664, -0.0948664, -0.0316285, 0.0316285, 0.0948664, 0.0948664], [255, 128, 64], True, False, False, ['none', 'none'], [], []],
    ['star', [-0.0353553, -0.0883883, -0.0353553, -0.0707107, -0.0176777, 0.0, 0.0176777, 0.0707107, 0.0353553, 0.0883883, 0.0353553, 0.0707107, 0.0176777, 0.0, -0.0176777, -0.0707107], [0.0176777, 0.0, -0.0176777, -0.0707107, -0.0353553, -0.0883883, -0.0353553, -0.0707107, -0.0176777, 0.0, 0.0176777, 0.0707107, 0.0353553, 0.0883883, 0.0353553, 0.0707107], [128, 0, 255], True, False, False, ['none', 'none'], [], []],
    ['triangle', [-0.0818157, 0.0818157, 0.0], [-0.0500008, -0.0500008, 0.1], [255, 0, 128], True, False, False, ['none', 'none'], [], []],
    ['cross', [-0.0707107, -0.0202091, -0.0707107, -0.0404041, 0.0, 0.0404041, 0.0707107, 0.0202091, 0.0707107, 0.0404041, 0.0, -0.0404041], [0.0707107, 0.0, -0.0707107, -0.0707107, -0.0100975, -0.0707107, -0.0707107, 0.0, 0.0707107, 0.0707107, 0.0100975, 0.0707107], [255, 0, 0], True, False, False, ['none', 'none'], [], []],       
    ['window', [0.0534515, 0.0534515, -0.0570026, -0.0570026, -0.0708093, -0.0708093, 0.0672582, 0.0672582, -0.0708093, -0.0570026], [0.0568051, -0.0536489, -0.0536489, 0.0429984, 0.0568051, -0.0674557, -0.0674557, 0.0706119, 0.0706119, 0.0568051], [255, 255, 0], True, False, False, ['none', 'none'], [], []],
    ['diamond', [0.0, -0.1, 0.0, 0.1], [0.1, 0.0, -0.1, 0.0], [0, 0, 255], True, False, False, ['none', 'none'], [], []],
    ['rect', [-0.0707107, 0.0707107, 0.0707107, -0.0707107], [0.0707107, 0.0707107, -0.0707107, -0.0707107], [255, 0, 255], True, False, False, ['none', 'none'], [], []],
    ['arrow1', [0.0484259, 0.0021048, 0.0021048, 0.0252654, 0.094747, 0.0484259, 0.0252654, -0.0210557, -0.0442163, -0.0442163, -0.0905373, -0.0210557], [-0.0424616, -0.0424616, -0.0193011, 0.0038595, 0.02702, 0.0501806, 0.0965017, 0.0501806, 0.0038595, -0.0424616, -0.0424616, -0.0887827], [255, 0, 0], True, False, False, ['none', 'none'], [], []],
    ['plus', [-0.0948664, -0.0948664, -0.0316285, -0.0316285, 0.0316285, 0.0316285, 0.0948664, 0.0948664, 0.0316285, 0.0316285, -0.0316285, -0.0316285], [0.0316285, -0.0316285, -0.0316285, -0.0948664, -0.0948664, -0.0316285, -0.0316285, 0.0316285, 0.0316285, 0.0948664, 0.0948664, 0.0316285], [0, 255, 0], True, False, False, ['none', 'none'], [], []],
    ['arrow2', [-0.0096108, 0.0144234, -0.0816992, -0.0576649, 0.0384433, 0.0624775, 0.0624775], [0.0624775, 0.0384433, -0.0576649, -0.0816992, 0.0144234, -0.0096108, 0.0624775], [0, 255, 255], True, False, False, ['none', 'none'], [], []]
]

class Series():

    def __init__(self, filepath : str, sections : dict):
        """Load the series file.
        
            Params:
                filepath (str): the filepath for the series JSON file
                sections (dict): snum : section basename for each section
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
        self.palette_traces = series_data["palette_traces"]

        for i in range(len(self.palette_traces)):
            self.palette_traces[i] = Trace.fromList(self.palette_traces[i])

        self.current_trace = Trace.fromList(series_data["current_trace"])

        self.ztraces = series_data["ztraces"]
        for name in self.ztraces:
            self.ztraces[name] = Ztrace.fromDict(name, self.ztraces[name])

        self.alignment = series_data["alignment"]
        self.object_groups = ObjGroupDict(series_data["object_groups"])
        self.object_3D_modes = series_data["object_3D_modes"]

        # keep track of transforms, mags, section thicknesses, and obj names
        self.section_tforms = {}
        self.section_mags = {}
        self.section_thicknesses = {}
        self.objs = set()

        # default settings
        self.modified_ztraces = []
        self.leave_open = False

        # possible zarr overlay
        self.zarr_overlay_fp = None
        self.zarr_overlay_group = None

        self.options = series_data["options"]

        # gather thickness, mag, and tforms for each section
        self.gatherSectionData()
    
    def gatherSectionData(self):
        """Get the mag, thickness, transforms, and object names from each section."""
        # THIS IS DONE THROUGH THE JSON METHOD TO SPEED IT UP
        for n, section in self.sections.items():
            # open the json
            filepath = os.path.join(
                self.getwdir(),
                section
            )
            with open(filepath, "r") as f:
                section_json = json.load(f)
            # get relevant data
            self.section_thicknesses[n] = section_json["thickness"]
            self.section_mags[n] = section_json["mag"]
            tforms = {}
            for a in section_json["tforms"]:
                tforms[a] = Transform(section_json["tforms"][a])
            self.section_tforms[n] = tforms
            for cname in section_json["contours"]:
                self.objs.add(cname)
    
    def updateSectionData(self, section : Section):
        """Get mag, thickness, transforms, and object names from a section."""
        n = section.n
        self.section_thicknesses[n] = section.thickness
        self.section_mags[n] = section.mag
        self.section_tforms[n] = section.tforms
        for cname in section.contours.keys():
            self.objs.add(cname)
    
    # OPENING, LOADING, AND MOVING THE JSER FILE
    # STATIC METHOD
    def openJser(fp : str):
        """Process the file containing all section and series information.
        
            Params:
                fp (str): the filepath
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
        
        # creating loading bar
        update, canceled = seriesProgbar(
            text="Opening series..."
        )
        progress = 0
        final_value = 1
        for sdata in jser_data["sections"]:
            if sdata: final_value += 1

        # create the hidden directory
        hidden_dir = createHiddenDir(sdir, sname)
        
        # extract JSON series data
        series_data = jser_data["series"]
        Series.updateJSON(series_data)
        series_fp = os.path.join(hidden_dir, sname + ".ser")
        with open(series_fp, "w") as f:
            json.dump(series_data, f)
        if canceled and canceled():
            return None
        progress += 1
        if update: update(progress/final_value * 100)

        # extract JSON section data
        sections = {}
        for snum, section_data in enumerate(jser_data["sections"]):
            # check for empty section, skip if so
            if section_data is None:
                continue

            filename = sname + "." + str(snum)
            section_fp = os.path.join(hidden_dir, filename)

            Section.updateJSON(section_data)  # update any missing attributes

            # gather the section numbers and section filenames
            sections[snum] = filename
                
            with open(section_fp, "w") as f:
                json.dump(section_data, f)
            
            if canceled and canceled():
                return None
            progress += 1
            if update:
                update(progress/final_value * 100)
        
        # create the series
        series = Series(series_fp, sections)
        series.jser_fp = fp
        
        return series

    def saveJser(self, close=False):
        """Save the jser file."""
        jser_data = {}

        filenames = os.listdir(self.hidden_dir)

        update, canceled = seriesProgbar(
            text="Saving series...",
            cancel=False
        )
        progress = 0
        final_value = len(filenames)

        # get the max section number
        sections_len = max(self.sections.keys())+1
        jser_data["sections"] = [None] * sections_len

        for filename in filenames:
            if "." not in filename:  # skip the timer file
                continue
            ext = filename[filename.rfind(".")+1:]
            if not (ext.isnumeric() or ext == "ser"):  # skip any other files
                continue
            fp = os.path.join(self.hidden_dir, filename)
            with open(fp, "r") as f:
                filedata = json.load(f)

            if ext.isnumeric():
                jser_data["sections"][int(ext)] = filedata
            else:
                jser_data["series"] = filedata

            if update: update(progress/final_value * 100)
            progress += 1
        
        save_str = json.dumps(jser_data)

        with open(self.jser_fp, "w") as f:
            f.write(save_str)
        
        # backup the series if requested
        if self.options["backup_dir"] and os.path.isdir(self.options["backup_dir"]):
            # get the file name
            fn = os.path.basename(self.jser_fp)
            # create the new file name
            t = datetime.now()
            dt = f"{t.year}{t.month:02d}{t.day:02d}_{t.hour:02d}{t.minute:02d}{t.second:02d}"
            fn = fn[:fn.rfind(".")] + "_" + dt + fn[fn.rfind("."):]
            # save the file
            backup_fp = os.path.join(
                self.options["backup_dir"],
                fn
            )
            with open(backup_fp, "w") as f:
                f.write(save_str)
        else:
            self.options["backup_dir"] = ""
        
        if close:
            self.close()
        else:
            self.gatherSectionData()

        if update: update(100)
    
    def move(self, new_jser_fp : str, section : Section, b_section : Section):
        """Move/rename the series to its jser filepath.
        
            Params:
                new_jser_fp (str): the new location for the series
                section (Section): the section file being used
                b_section (Section): the secondary section file being used
            """
        # move/rename the hidden directory
        old_name = self.name
        new_name = os.path.basename(new_jser_fp)
        new_name = new_name[:new_name.rfind(".")]
        old_hidden_dir = os.path.dirname(self.filepath)
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
        self.rename(new_name)

        # change the filepaths for the series and section files
        self.jser_fp = new_jser_fp
        self.hidden_dir = new_hidden_dir
        self.filepath = os.path.join(
            new_hidden_dir,
            os.path.basename(self.filepath).replace(old_name, new_name)
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
    
    def close(self):
        """Clear the hidden directory of the series."""
        if self.leave_open:
            return
        if os.path.isdir(self.hidden_dir):
            for f in os.listdir(self.hidden_dir):
                os.remove(os.path.join(self.hidden_dir, f))
            os.rmdir(self.hidden_dir)
    
    # STATIC METHOD
    def updateJSON(series_data):
        """Add missing attributes to the series JSON."""
        empty_series = Series.getEmptyDict()
        for key in empty_series:
            if key not in series_data:
                series_data[key] = empty_series[key]
        for key in empty_series["options"]:
            if key not in series_data["options"]:
                series_data["options"][key] = empty_series["options"][key]
        
        # check for backup_dir key
        if "backup_dir" in series_data:
            series_data["options"]["backup_dir"] = series_data["backup_dir"]
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
        
        # check the traces (convert dicts to lists)
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
                    trace["history"]
                ]
                series_data["palette_traces"][i] = trace
        trace = series_data["current_trace"]
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
                trace["history"]
            ]
            series_data["current_trace"] = trace

    def getDict(self) -> dict:
        """Convert series object into a dictionary.
        
            Returns:
                (dict) all of the compiled section data
        """
        d = {}
        
        # d["sections"] = self.sections
        d["current_section"] = self.current_section
        d["src_dir"] = self.src_dir
        d["window"] = self.window
        d["palette_traces"] = []
        
        for trace in self.palette_traces:
            d["palette_traces"].append(trace.getList())
            
        d["current_trace"] = self.current_trace.getList()

        d["ztraces"] = {}
        for name in self.ztraces:
            d["ztraces"][name] = self.ztraces[name].getDict()
            
        d["alignment"] = self.alignment
        d["object_groups"] = self.object_groups.getGroupDict()
        d["object_3D_modes"] = self.object_3D_modes

        # ADDED SINCE JAN 25TH
        d["options"] = self.options

        return d
    
    # STATIC METHOD
    def getEmptyDict():
        """Get an empty dictionary for a series object."""
        series_data = {}
        
        # series_data["sections"] = {}  # section_number : section_filename
        series_data["current_section"] = 0  # last section left off
        series_data["src_dir"] = ""  # the directory of the images
        series_data["window"] = [0, 0, 1, 1] # x, y, w, h of reconstruct window in field coordinates
        series_data["palette_traces"] = [t.getList(include_name=True) for t in Series.getDefaultPaletteTraces()]
        series_data["current_trace"] = series_data["palette_traces"][0]
        series_data["ztraces"] = []
        series_data["alignment"] = "default"
        series_data["object_groups"] = {}
        series_data["object_3D_modes"] = {}

        # ADDED SINCE JAN 25TH

        series_data["options"] = {}

        options = series_data["options"]
        options["autosave"] = False
        options["3D_smoothing"] = "humphrey"
        options["small_dist"] = 0.01
        options["med_dist"] = 0.1
        options["big_dist"] = 1
        options["show_ztraces"] = True
        options["backup_dir"] = ""
        options["fill_opacity"] = 0.2
        options["grid"] = [1, 1, 1, 1, 1, 1]
        options["pointer"] = ["lasso", "exc"]
        options["show_ztraces"] = False
        options["find_zoom"] = 95
        options["autoseg"] = {}

        return series_data
    
    # STATIC METHOD
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
            hidden_dir = createHiddenDir(wdir, series_name)
        except PermissionError:
            print("Series cannot be created adjacent to images due to permissions; \
                   creating in home folder instead.")
            if os.name == "nt":
                wdir = os.environ.get("HOMEPATH")
            else:
                wdir = os.environ.get("HOME")
            hidden_dir = createHiddenDir(wdir, series_name)

        series_data = Series.getEmptyDict()

        series_data["src_dir"] = wdir  # the directory of the images
        sections = {}
        for i in range(len(image_locations)):
            sections[i] = series_name + "." + str(i)

        series_fp = os.path.join(hidden_dir, series_name + ".ser")
        with open(series_fp, "w") as series_file:
            series_file.write(json.dumps(series_data, indent=2))
        
        # create section files (.#)
        for i in range(len(image_locations)):
            Section.new(series_name, i, image_locations[i], mag, thickness, hidden_dir)

        # create series object
        series = Series(series_fp, sections)
        
        # save the jser file
        # series.jser_fp = os.path.join(
        #     wdir,
        #     f"{series_name}.jser"
        # )
        # series.saveJser()
        
        return series
    
    def isWelcomeSeries(self):
        """Return True if self is the welcome series."""
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
        """
        section = Section(section_num, self)
        # update transform data
        self.section_tforms[section.n] = section.tforms
        self.section_mags[section.n] = section.mag
        self.section_thicknesses[section.n] = section.thickness
        return section
    
    def enumerateSections(self, show_progress=True, message="Loading series data..."):
        """Allow iteration through the sections."""
        return SeriesIterator(self, show_progress, message)

    def map(self, fn, *args, message=None):
        """Map a function to every section in the series.
        
            Params:
                fn (function): the function to run on the section
                *args: the arguments to pass into the function AFTER the section
        """
        # create wrapper func
        results = {}
        def wrapper(snum, fn, *args):
            section = self.loadSection(snum)
            results[snum] = fn(section, *args)

        # create progress bar
        if message:
            update, _ = seriesProgbar(text=message, cancel=False)
            self.threadpool = ThreadPool(update=update)
        else:
            self.threadpool = ThreadPool()
        
        # create and run threadpool
        for snum in self.sections:
            self.threadpool.createWorker(
                wrapper,
                snum,
                fn,
                *args
            )
        self.threadpool.startAll(finished_fn=None)
        self.threadpool.waitForDone(-1)

        return results

    def modifyAlignments(self, add : list = [], remove : list = [], rename : list = []):
        """Modify the alignments (input from dialog).
        
            Params:
                add (list): the alignments to add
                remove (list): the alignments to remove
                rename (list): the alignments to rename (old, new)
        """
        if not (add or remove or rename):
            return
        for snum, section in self.enumerateSections(message="Modifying alignments..."):
            for a in add:
                section.tforms[a] = section.tforms[self.alignment]
            for a, new_name in rename:
                if a in section.tforms:
                    section.tforms[new_name] = section.tforms[a]
                    del(section.tforms[a])
            for a in remove:
                if a in section.tforms:
                    del(section.tforms[a])
            section.save()
    
    def getZValues(self):
        """Return the z-values for each section.
        
            Returns:
                (dict): section number : z-value
        """
        zvals = {}
        z = 0
        for snum in sorted(self.section_thicknesses.keys()):
            t = self.section_thicknesses[snum]
            z += t
            zvals[snum] = z
        
        return zvals
    
    def createZtrace(self, obj_name : str, cross_sectioned=True):
        """Create a ztrace from an existing object in the series.
        
            Params:
                obj_name (str): the name of the object to create the ztrace from
                cross_sectioned (bool): True if one ztrace point per section, False if multiple per section
        """
        # delete an existing ztrace with the same name
        if obj_name in self.ztraces:
            del(self.ztraces[obj_name])

        color = None
        
        # if cross-sectioned object (if create on midpoints), make one point per section
        if cross_sectioned:
            points = []
            for snum, section in self.enumerateSections(
                message="Creating ztrace..."
            ):
                if obj_name in section.contours:
                    if not color: color = section.contours[obj_name][0].color
                    contour = section.contours[obj_name]
                    p = (*contour.getMidpoint(), snum)
                    points.append(p)
                    
        # otherwise, make points by trace history by section
        # each trace gets its own point, ztrace points are in chronological order based on trace history
        else:
            dt_points = []
            for snum, section in self.enumerateSections(
                message="Creating ztrace..."
            ):
                if obj_name in section.contours:
                    contour = section.contours[obj_name]
                    for trace in contour:
                        if not color: color = trace.color
                        # get the trace creation datetime
                        dt = trace.history[0].dt
                        # get the midpoint
                        p = (*trace.getMidpoint(), snum)
                        dt_points.append((snum, dt, p))
            # sort the points by datetime
            dt_points.sort()
            points = [dtp[2] for dtp in dt_points]
        
        self.ztraces[obj_name] = Ztrace(obj_name, color, points)

        self.modified = True
    
    def editZtraceAttributes(self, ztrace : Ztrace, name : str, color : tuple):
        """Edit the name and color of a ztrace.
        
            Params:
                ztrace (Ztrace): the ztrace object to modify
                name (str): the new name
                color (tuple): the new color
        """
        if name:
            del(self.ztraces[ztrace.name])
            ztrace.name = name
            self.ztraces[name] = ztrace
        if color:
            ztrace.color = color
        
        self.modified = True
        
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
    
    def deleteObjects(self, obj_names : list):
        """Delete object(s) from the series.
        
            Params:
                obj_names (list): the objects to delete
        """
        # remove objects from their groups
        for name in obj_names:
            self.object_groups.removeObject(name)
        for snum, section in self.enumerateSections(
            message="Deleting object(s)..."
        ):
            modified = False
            for obj_name in obj_names:
                if obj_name in section.contours:
                    del(section.contours[obj_name])
                    modified = True
            
            if modified:
                section.save()
        
        self.modified = True
    
    def editObjectAttributes(self, obj_names : list, name : str = None, color : tuple = None, tags : set = None, mode : tuple = None, addTrace=None):
        """Edit the attributes of objects on every section.
        
            Params:
                series (Series): the series object
                obj_names (list): the names of the objects to rename
                name (str): the new name for the objects
                color (tuple): the new color for the objects
                addTrace (function): for object table updating purposes
        """
        # modify the object on every section
        for snum, section in self.enumerateSections(
            message="Modifying object(s)..."
        ):
            traces = []
            for obj_name in obj_names:
                if obj_name in section.contours:
                    traces += section.contours[obj_name].getTraces()
            if traces:
                section.editTraceAttributes(traces, name, color, tags, mode, add_tags=True)
                # gather new traces
                if name:
                    traces = section.contours[name].getTraces()
                else:
                    traces = []
                    for obj_name in obj_names:
                        if obj_name in section.contours:
                            traces += section.contours[obj_name].getTraces()
                # add trace data to table data
                if addTrace:
                    for trace in traces:
                        addTrace(trace, section, snum)
                section.save()
        
        self.modified = True
    
    def editObjectRadius(self, obj_names : list, new_rad : float, addTrace=None):
        """Change the radii of all traces of an object.
        
            Params:
                obj_names (list): the names of objects to modify
                new_rad (float): the new radius for the traces of the object
                addTrace (function): for object table updating purposes
        """
        for snum, section in self.enumerateSections(
            message="Modifying radii..."
        ):
            traces = []
            for name in obj_names:
                if name in section.contours:
                    traces += section.contours[name].getTraces()
            if traces:
                section.editTraceRadius(traces, new_rad)
                # add trace data to table data
                if addTrace:
                    for trace in traces:
                        addTrace(trace, section, snum)
                section.save()
        
        self.modified = True
    
    def editObjectShape(self, obj_names : list, new_shape : float, addTrace=None):
        """Change the shape of all traces of an object.
        
            Params:
                obj_names (list): the names of objects to modify
                new_shape (list): the new shape for the traces of the object
                addTrace (function): for object table updating purposes
        """
        for snum, section in self.enumerateSections(
            message="Modifying shapes..."
        ):
            traces = []
            for name in obj_names:
                if name in section.contours:
                    traces += section.contours[name].getTraces()
            if traces:
                section.editTraceShape(traces, new_shape)
                # add trace data to table data
                if addTrace:
                    for trace in traces:
                        addTrace(trace, section, snum)
                section.save()
        
        self.modified = True
    
    def removeAllTraceTags(self, obj_names : list):
        """Remove all tags from all traces on a set of objects.
        
            Params:
                obj_names (list): a list of object names
        """
        for snum, section in self.enumerateSections(
            message="Removing trace tags..."
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
                )
                section.save()

        self.modified = True
    
    def hideObjects(self, obj_names : list, hide=True):
        """Hide all traces of a set of objects throughout the series.
        
            Params:
                obj_names (list): the names of objects to hide
                hide (bool): True if object should be hidden
        """
        for snum, section in self.enumerateSections(
            message="Hiding object(s)..." if hide else "Unhiding object(s)..."
        ):
            modified = False
            for name in obj_names:
                if name in section.contours:
                    contour = section.contours[name]
                    for trace in contour:
                        trace.setHidden(hide)
                        modified = True
            if modified:
                section.save()
        
        self.modified = True
    
    def hideAllTraces(self, hidden=True):
        """Hide all traces in the entire series.
        
            Params:
                hidden (bool): True if traces are to be hidden
        """
        for snum, section in self.enumerateSections(
            message="Hiding traces..." if hidden else "Unhiding traces..."):
            for trace in section.tracesAsList():
                trace.setHidden(hidden)
            section.save()
    
    def importTraces(self, other):
        """Import all the traces from another series."""
        # ensure that the two series have the same sections
        if sorted(list(self.sections.keys())) != sorted(list(other.sections.keys())):
            return
        
        iterator = zip(self.enumerateSections(), other.enumerateSections(show_progress=False))
        for (r_num, r_section), (s_num, s_section) in iterator:
            r_section.importTraces(s_section)
        
        self.save()
        self.gatherSectionData()
    
    def importZtraces(self, other):
        """Import all the ztraces from another series."""
        for o_zname, o_ztrace in other.ztraces.items():
            # only import new ztraces, do NOT replace existing ones
            if o_zname not in self.ztraces:
                self.ztraces[o_zname] = o_ztrace.copy()
        
        self.save()
    
    def importTransforms(self, other, alignments : list):
        """Import transforms from another series.
        
            Params:
                other (series): the series to import transforms from
                alignments (list): the names of alignments to import
        """
        # ensure that the two series have the same sections
        if sorted(list(self.sections.keys())) != sorted(list(other.sections.keys())):
            return
        
        iterator = zip(self.enumerateSections(), other.enumerateSections(show_progress=False))
        for (r_num, r_section), (s_num, s_section) in iterator:
            for a in alignments:
                r_section.tforms[a] = s_section.tforms[a].copy()
                r_section.save()
                self.section_tforms[r_num][a] = s_section.tforms[a].copy()
                
        self.save()
    
    def loadObjectData(self, object_table_items=False):
        """Load all of the data for each object in the series.
        
        Params:
            object_table_items (bool): True if dictionary values should be ObjectTableItem objects
        Returns:
            (dict): object_name : object_data
        """

        objdict = {}  # object name : ObjectTableItem (contains data on object)

        for snum, section in self.enumerateSections():
            # iterate through contours
            for contour_name in section.contours:
                if contour_name not in objdict:
                    objdict[contour_name] = ObjectTableItem(contour_name)
                # iterate through traces
                for trace in section.contours[contour_name]:
                    # add to existing data
                    objdict[contour_name].addTrace(
                        trace,
                        section.tforms[self.alignment],
                        snum,
                        section.thickness
                    )
        
        if not object_table_items:
            for name, item in objdict.items():
                objdict[name] = item.getDict()
                # add the object group to the data
                objdict[name]["groups"] = self.object_groups.getObjectGroups(name)

        return objdict

    # STATIC METHOD
    def getDefaultPaletteTraces():
        """Return the default palette trace list."""
        palette_traces = []
        for l in default_traces:
            palette_traces.append(Trace.fromList(l.copy()))
        return palette_traces * 2

    def mergeObjects(self, obj_names : list, new_name : str):
        """Merge objects on every section.
        
            Params:
                obj_names (list): the names of the objects to merge
                new_name (str): the name for the merged object
        """
        # iterate through sections
        for snum, section in self.enumerateSections(message="Merging objects..."):
            # get the traces to modify
            traces = []
            for name in obj_names:
                if name in section.contours:
                    traces += section.contours[name].getTraces()
                    del(section.contours[name])
            if not traces:
                continue

            # get the color
            color = traces[0].color
            fill_mode = traces[0].fill_mode

            # get the mag
            if self.screen_mag:
                mag = self.screen_mag
            else:
                mag = section.mag

            # iterate through and gather pixel points
            pix_traces = []
            for trace in traces:
                trace.name = new_name
                pix_traces.append(
                    [(round(x / mag), round(y / mag)) for x, y in trace.points]
                )
            
            # merge the traces
            new_pix_traces = mergeTraces(pix_traces)

            # create a new contour from the traces
            for pix_trace in new_pix_traces:
                # convert pixels back to field coords
                field_points = [
                    (x * mag, y * mag) for x, y in pix_trace
                ]
                # create the trace
                trace = Trace(new_name, color)
                trace.fill_mode = fill_mode
                trace.points = field_points
                # add it to the contour
                section.addTrace(trace, "Created by merging objects")

            # save thes section
            section.save()
    
    def getRecentSegGroup(self):
        """Return the most recent segmentation group name."""
        g = None
        for group in self.object_groups.getGroupList():
            if group.startswith("seg_") and (
                g is None or group > g
            ):
                g = group
        return g



class SeriesIterator():

    def __init__(self, series : Series, show_progress : bool, message : str):
        """Create the series iterator object.
        
            Params:
                series (Series): the series object
                show_progress (bool): show progress dialog if True
        """
        self.series = series
        self.show_progress = show_progress
        self.message = message
    
    def __iter__(self):
        """Allow the user to iterate through the sections."""
        self.section_numbers = sorted(list(self.series.sections.keys()))
        self.sni = 0
        if self.show_progress:
            self.update, canceled = seriesProgbar(
                text=self.message,
                cancel=False
            )
        return self
    
    def __next__(self):
        """Return the next section."""
        if self.sni < len(self.section_numbers):
            if self.show_progress:
                if self.update:
                    self.update(self.sni / len(self.section_numbers) * 100)
            snum = self.section_numbers[self.sni]
            section = self.series.loadSection(snum)
            self.sni += 1
            return snum, section
        else:
            if self.show_progress:
                if self.update:
                    self.update(self.sni / len(self.section_numbers) * 100)
            raise StopIteration


class BasicProgbar():
    def __init__(self, text : str):
        """Create a 'vanilla' progress indicator.
        
        Params:
            text (str): the text to display by the indicator
        """
        self.text = text
        print(f"{text} | 0.0%", end="\r")
    
    def update(self, p):
        """Update the progress indicator.
        
            Params:
                p (float): the percentage of progress made
        """
        print(f"{self.text} | {p:.1f}%", end="\r")
        if p == 100:
            print()
    
    def canceled(self):
        """Dummy function -- do nothing!"""
        return False

def seriesProgbar(text : str, cancel : bool = True):
    """Return the appropriate progress bar for the situation.
    
        text (str): the text to display on the progress bar
        cancel (bool): True if progress can be canceled
    """
    use_basic = not prog_imported
    if prog_imported:
        update, canceled = progbar(
            title=" ",
            text=text,
            cancel=cancel
        )
        if update is None:
            use_basic = True
    if use_basic:
        pbar = BasicProgbar(text)
        update = pbar.update
        canceled = pbar.canceled
    
    return update, canceled
