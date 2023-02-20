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

        # keep track of transforms, mags, and section thicknesses
        self.section_tforms = {}
        self.section_mags = {}
        self.section_thicknesses = {}

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
        for key in empty_series["options"]:
            if key not in series_data["options"]:
                series_data["options"][key] = empty_series["options"][key]
        
        # check the ztraces
        for ztrace in series_data["ztraces"]:
            if "color" not in ztrace:
                ztrace["color"] = (255, 255, 0)

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
        options["show_ztraces"] = True

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
        section = Section(section_num, self)
        # update transform data
        self.section_tforms[section.n] = section.tforms
        self.section_mags[section.n] = section.mag
        self.section_thicknesses[section.n] = section.thickness
        return section
    
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
        
        self.modified = True
    
    def createZtrace(self, obj_name : str, cross_sectioned=True):
        """Create a ztrace from an existing object in the series.
        
            Params:
                obj_name (str): the name of the object to create the ztrace from
                cross_sectioned (bool): True if one ztrace point per section, False if multiple per section
        """
        for ztrace in self.ztraces:
            if obj_name == ztrace.name:
                self.ztraces.remove(ztrace)
                break
        color = None
        # if cross-sectioned object, make one point per section
        if cross_sectioned:
            points = []
            for snum, section in self.enumerateSections(
                show_progress=False
            ):
                if obj_name in section.contours:
                    if not color: color = section.contours[obj_name][0].color
                    contour = section.contours[obj_name]
                    p = (*contour.getMidpoint(), snum)
                    points.append(p)
        # if not cross-sectioned, make points by trace history
        else:
            dt_points = []
            for snum, section in self.enumerateSections(
                show_progress=False
            ):
                if obj_name in section.contours:
                    contour = section.contours[obj_name]
                    for trace in contour:
                        if not color: color = trace.color
                        # get the trace creation datetime
                        dt = trace.history[0].dt
                        # get the midpoint
                        p = (*trace.getMidpoint(), snum)
                        dt_points.append((dt, p))
            # sort the points by datetime
            dt_points.sort()
            points = [dtp[1] for dtp in dt_points]
        
        self.ztraces.append(Ztrace(obj_name, color, points))

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
