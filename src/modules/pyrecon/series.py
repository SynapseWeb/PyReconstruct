import os
import json

from modules.pyrecon.ztrace import Ztrace
from modules.pyrecon.section import Section
from modules.pyrecon.trace import Trace

from modules.pyrecon.obj_group_dict import ObjGroupDict

from constants.locations import createHiddenDir, assets_dir
from constants.defaults import getDefaultPaletteTraces

from modules.gui.gui_functions import progbar

class Series():

    def __init__(self, filepath : str):
        """Load the series file.
        
            Params:
                filepath (str): the filepath for the series JSON file
        """
        self.filepath = filepath
        self.name = os.path.basename(self.filepath)[:-4]

        with open(filepath, "r") as f:
            series_data = json.load(f)

        Series.updateJSON(series_data)

        self.jser_fp = ""
        self.hidden_dir = os.path.dirname(self.filepath)
        self.modified = False

        self.sections = {}  # section number : section file

        for section_num, section_filename in series_data["sections"].items():
            self.sections[int(section_num)] = section_filename

        self.current_section = series_data["current_section"]
        self.src_dir = series_data["src_dir"]
        self.screen_mag = 0  # default value for screen mag (will be calculated when generateView called)
        self.window = series_data["window"]
        self.palette_traces = series_data["palette_traces"]

        for i in range(len(self.palette_traces)):
            self.palette_traces[i] = Trace.fromDict(self.palette_traces[i])

        self.current_trace = Trace.fromDict(series_data["current_trace"])
        self.ztraces = series_data["ztraces"]

        for i in range(len(self.ztraces)):
            self.ztraces[i] = Ztrace.fromDict(self.ztraces[i])

        self.alignment = series_data["alignment"]
        self.object_groups = ObjGroupDict(series_data["object_groups"])
        self.object_3D_modes = series_data["object_3D_modes"]
        self.backup_dir = series_data["backup_dir"]

        # default settings
        self.fill_opacity = 0.2

        # ADDED SINCE JAN 25TH

        self.options = series_data["options"]
    
    # STATIC METHOD
    def updateJSON(series_data):
        """Add missing attributes to the series JSON."""
        empty_series = Series.getEmptyDict()
        for key in empty_series:
            if key not in series_data:
                series_data[key] = empty_series[key]

    def getDict(self) -> dict:
        """Convert series object into a dictionary.
        
            Returns:
                (dict) all of the compiled section data
        """
        d = {}
        
        d["sections"] = self.sections
        d["current_section"] = self.current_section
        d["src_dir"] = self.src_dir
        d["window"] = self.window
        d["palette_traces"] = []
        
        for trace in self.palette_traces:
            d["palette_traces"].append(trace.getDict())
            
        d["current_trace"] = self.current_trace.getDict()
        d["ztraces"] = []
        
        for ztrace in self.ztraces:
            d["ztraces"].append(ztrace.getDict())
            
        d["alignment"] = self.alignment
        d["object_groups"] = self.object_groups.getGroupDict()
        d["object_3D_modes"] = self.object_3D_modes
        d["backup_dir"] = self.backup_dir

        # ADDED SINCE JAN 25TH
        d["options"] = self.options

        return d
    
    # STATIC METHOD
    def getEmptyDict():
        """Get an empty dictionary for a series object."""
        series_data = {}
        
        series_data["sections"] = {}  # section_number : section_filename
        series_data["current_section"] = 0  # last section left off
        series_data["src_dir"] = ""  # the directory of the images
        series_data["window"] = [0, 0, 1, 1] # x, y, w, h of reconstruct window in field coordinates
        series_data["palette_traces"] = getDefaultPaletteTraces()  # trace palette
        series_data["current_trace"] = series_data["palette_traces"][0]
        series_data["ztraces"] = []
        series_data["alignment"] = "default"
        series_data["object_groups"] = {}
        series_data["object_3D_modes"] = {}
        series_data["backup_dir"] = ""

        # ADDED SINCE JAN 25TH

        series_data["options"] = {}

        options = series_data["options"]
        options["autosave"] = False
        options["3D_smoothing"] = "laplacian"
        options["small_dist"] = 0.01
        options["med_dist"] = 0.1
        options["big_dist"] = 1

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
        wdir = os.path.dirname(image_locations[0])
        hidden_dir = createHiddenDir(wdir, series_name)
        series_data = Series.getEmptyDict()

        series_data["src_dir"] = wdir  # the directory of the images
        for i in range(len(image_locations)):
            series_data["sections"][i] = series_name + "." + str(i)

        series_fp = os.path.join(hidden_dir, series_name + ".ser")
        with open(series_fp, "w") as series_file:
            series_file.write(json.dumps(series_data, indent=2))
        
        # create section files (.#)
        for i in range(len(image_locations)):
            Section.new(series_name, i, image_locations[i], mag, thickness, hidden_dir)
        
        return Series(series_fp)
    
    def isWelcomeSeries(self):
        """Return True if self is the welcome series."""
        try:
            if os.path.samefile(self.filepath, os.path.join(assets_dir, "welcome_series", "welcome.ser")):
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
        return Section(section_num, self)
    
    def enumerateSections(self, show_progress=True, message="Loading series data..."):
        """Allow iteration through the sections."""
        return SeriesIterator(self, show_progress, message)
    
    def newAlignment(self, alignment_name : str, base_alignment="default"):
        """Create a new alignment.
        
            Params:
                alignment_name (str): the name of the new alignment
                base_alignment (str): the name of the reference alignment for this new alignment
        """
        for snum in self.sections:
            section = self.loadSection(snum)
            section.tforms[alignment_name] = section.tforms[base_alignment]
            section.save()
    
    def createZtrace(self, obj_name : str):
        """Create a ztrace from an existing object in the series.
        
            Params:
                obj_name (str): the name of the object to create the ztrace from
        """
        for ztrace in self.ztraces:
            if obj_name == ztrace.name:
                self.ztraces.remove(ztrace)
                break
        points = []
        for snum in sorted(self.sections.keys()):
            section = self.loadSection(snum)
            if obj_name in section.contours:
                contour = section.contours[obj_name]
                p = (*contour.getMidpoint(), snum)
                points.append(p)
        self.ztraces.append(Ztrace(obj_name, points))
    
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
            self.update, canceled = progbar(
                title=" ",
                text=self.message,
                cancel=False
            )
        return self
    
    def __next__(self):
        """Return the next section."""
        if self.sni < len(self.section_numbers):
            if self.show_progress:
                self.update(self.sni / len(self.section_numbers) * 100)
            snum = self.section_numbers[self.sni]
            section = self.series.loadSection(snum)
            self.sni += 1
            return snum, section
        else:
            if self.show_progress:
                self.update(self.sni / len(self.section_numbers) * 100)
            raise StopIteration
