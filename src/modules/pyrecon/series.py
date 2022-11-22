import os
import json
from .trace import Trace

from modules.legacy_recon.utils.reconstruct_reader import process_series_file
from modules.legacy_recon.utils.reconstruct_writer import write_series

from modules.pyrecon.ztrace import Ztrace
from modules.pyrecon.section import Section
from modules.pyrecon.trace import Trace

from modules.pyrecon.obj_group_dict import ObjGroupDict

from constants.locations import assets_dir
from constants.defaults import getDefaultPaletteTraces

class Series():

    def __init__(self, filepath : str):
        """Load the series file.
        
            Params:
                filepath (str): the filepath for the series JSON file
        """
        self.filepath = filepath

        try:
            with open(filepath, "r") as f:
                series_data = json.load(f)
            self.filetype = "JSON"
        except json.decoder.JSONDecodeError:
            self.filetype = "XML"
        
        if self.filetype == "JSON":
            self.sections = {}  # section number : section file
            for section_num, section_filename in series_data["sections"].items():
                self.sections[int(section_num)] = section_filename
            self.current_section = series_data["current_section"]
            self.src_dir = series_data["src_dir"]
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

        
        elif self.filetype == "XML":
            self.xml_series = process_series_file(filepath)

            # get each of the section filenames
            self.sections = {}
            series_file = os.path.basename(filepath)
            series_name = series_file[:series_file.rfind(".")]
            series_dir = os.path.dirname(filepath)
            for filename in os.listdir(series_dir):
                ext = filename[filename.rfind(".")+1:]
                if ext.isnumeric() and filename.startswith(series_name):
                    self.sections[int(ext)] = filename
            
            self.current_section = self.xml_series.index
            self.src_dir = ""
            self.window = list(self.xml_series.viewport[:2]) + [5, 5]
            self.palette_traces = []
            for xml_contour in self.xml_series.contours:
                self.palette_traces.append(Trace.fromXMLObj(xml_contour))
            self.current_trace = self.palette_traces[0]
            self.ztraces = []  # should eventually be changed
            self.alignment = "default"
            self.object_groups = ObjGroupDict()
    
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
        return d
    
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
        series_data = {}
        series_data["sections"] = {}  # section_number : section_filename
        series_data["current_section"] = 0  # last section left off
        series_data["src_dir"] = ""  # the directory of the images
        series_data["window"] = [0, 0, 1, 1] # x, y, w, h of reconstruct window in field coordinates
        for i in range(len(image_locations)):
            series_data["sections"][i] = series_name + "." + str(i)
        series_data["palette_traces"] = getDefaultPaletteTraces()  # trace palette
        series_data["current_trace"] = series_data["palette_traces"][0]
        series_data["ztraces"] = []
        series_data["alignment"] = "default"
        series_data["object_groups"] = ObjGroupDict()

        series_fp = os.path.join(wdir, series_name + ".ser")
        with open(series_fp, "w") as series_file:
            series_file.write(json.dumps(series_data, indent=2))
        
        # create section files (.#)
        for i in range(len(image_locations)):
            Section.new(series_name, i, image_locations[i], mag, thickness, wdir)
        
        return Series(series_fp)
        
    def save(self):
        """Save file into json."""
        if self.filepath == assets_dir + "/welcome_series/welcome.ser":
            return  # ignore welcome series

        if self.filetype == "JSON":
            d = self.getDict()
            with open(self.filepath, "w") as f:
                f.write(json.dumps(d, indent=1))
        
        elif self.filetype == "XML":
            self.xml_series.index = self.current_section
            self.xml_series.viewport = tuple(self.window[:2]) + (self.xml_series.viewport[2],)
            self.xml_series.contours = []
            for trace in self.palette_traces:
                self.xml_series.contours.append(trace.getXMLObj())
            write_series(self.xml_series, directory=os.path.dirname(self.filepath), outpath=self.filepath, overwrite=True)
    
    def getwdir(self):
        return os.path.dirname(self.filepath)
    
    def loadSection(self, section_num : int) -> Section:
        """Load a section object.
        
            Params:
                section_num (int): the section number
        """
        return Section(os.path.join(self.getwdir(), self.sections[section_num]))
    
    def newAlignment(self, alignment_name : str, base_alignment="default"):
        if self.filetype == "XML":
            print("Alignments not support for XML files.")
            print("Please export your series as JSON.")
        for snum in self.sections:
            section = self.loadSection(snum)
            section.tforms[alignment_name] = section.tforms[base_alignment]
            section.save()
    
    def createZtrace(self, obj_name : str):
        """Create a ztrace from an existing object in the series.
        
            Params:
                obj_name (str): the name of the object to create the ztrace from
        """
        points = []
        for snum in self.sections:
            section = self.loadSection(snum)
            if obj_name in section.contours:
                contour = section.contours[obj_name]
                p = (*contour.getMidpoint(), snum)
                points.append(p)
        self.ztraces.append(Ztrace(obj_name, points))

                
