import os
import json
from .trace import Trace

from modules.legacy_recon.classes.transform import Transform as XMLTransform
from modules.legacy_recon.utils.reconstruct_reader import process_section_file
from modules.legacy_recon.utils.reconstruct_writer import write_section

from constants.locations import assets_dir

class Section():

    def __init__(self, filepath : str):
        """Load the section file.
        
            Params:
                filepath (str): the file path for the section JSON or XML file
        """
        self.filepath = filepath
        self.contours_to_update = set()

        try:
            with open(filepath, "r") as f:
                section_data = json.load(f)
            self.filetype = "JSON"
        except json.decoder.JSONDecodeError:
            self.filetype = "XML"
        
        if self.filetype == "JSON":
            self.src = section_data["src"]
            self.brightness = section_data["brightness"]
            self.contrast = section_data["contrast"]
            self.mag = section_data["mag"]
            self.tforms = section_data["tforms"]
            self.thickness = section_data["thickness"]
            self.contours = section_data["traces"]
            for name in self.contours:
                for i in range(len(self.contours[name])):  # convert trace dictionaries into trace objects
                    self.contours[name][i] = Trace.fromDict(self.contours[name][i])
        
        elif self.filetype == "XML":
            self.xml_section = process_section_file(filepath)
            image = self.xml_section.images[0] # assume only one image
            self.tforms = {}
            self.tforms["default"] = list(image.transform.tform()[:2,:].reshape(6))
            self.src = image.src
            self.brightness = 0
            self.contrast = 0
            self.mag = image.mag
            self.thickness = self.xml_section.thickness
            self.contours = {}
            for xml_contour in self.xml_section.contours:
                self.addTrace(Trace.fromXMLObj(xml_contour, image.transform))
    
    def addTrace(self, trace : Trace):
        """Add a trace to the trace dictionary.
        
            Params:
                trace (Trace): the trace to add
        """
        # insert username as first tag
        trace.tags = set((os.getlogin(),)).union(trace.tags)

        if trace.name in self.contours:
            self.contours[trace.name].append(trace)
        else:
            self.contours[trace.name] = [trace]
        
        self.contours_to_update.add(trace.name)
    
    def removeTrace(self, trace : Trace):
        """Remove a trace from the trace dictionary.
        
            Params:
                trace (Trace): the trace to remove from the traces dictionary
        """
        if trace.name in self.contours:
            self.contours[trace.name].remove(trace)
        
        self.contours_to_update.add(trace.name)
    
    def tracesAsList(self) -> list[Trace]:
        """Return the trace dictionary as a list. Does NOT copy traces.
        
            Returns:
                (list): a list of traces
        """
        trace_list = []
        for contour_name in self.contours:
            for trace in self.contours[contour_name]:
                trace_list.append(trace)
        return trace_list

    def getDict(self) -> dict:
        """Convert section object into a dictionary.
        
            Returns:
                (dict) all of the compiled section data
        """
        d = {}
        d["src"] = self.src
        d["brightness"] = self.brightness
        d["contrast"] = self.contrast
        d["mag"] = self.mag
        d["tforms"] = self.tforms
        d["thickness"] = self.thickness
        d["traces"] = {}
        # special saving method for contours
        for contour_name in self.contours:
            if self.contours[contour_name] != []:
                d["traces"][contour_name] = self.contours[contour_name].copy()
                for i in range(len(d["traces"][contour_name])):  # convert trace objects in trace dictionaries
                    d["traces"][contour_name][i] = d["traces"][contour_name][i].getDict()
        return d
    
    # STATIC METHOD
    def new(series_name : str, snum : int, image_location : str, mag : float, thickness : float, wdir : str):
        """Create a new blank section file.
        
            Params:
                series_name (str): the name for the series
                snum (int): the sectino number
                image_location (str): the file path for the image
                mag (float): microns per pixel for the section
                thickness (float): the section thickness in microns
                wdir (str): the working directory for the sections
            Returns:
                (Section): the newly created section object
        """
        section_data = {}
        section_data["src"] = os.path.basename(image_location)  # image location
        section_data["brightness"] = 0
        section_data["contrast"] = 0
        section_data["mag"] = mag  # microns per pixel
        section_data["thickness"] = thickness  # section thickness
        section_data["tforms"] = {}  
        section_data["tforms"]["default"]= [1, 0, 0, 0, 1, 0] # identity matrix default
        section_data["traces"] = {}
        section_fp = os.path.join(wdir, series_name + "." + str(snum))
        with open(section_fp, "w") as section_file:
            section_file.write(json.dumps(section_data, indent=2))
        return Section(section_fp)
   
    def save(self):
        """Save file into json or xml."""
        try:
            if os.path.samefile(self.filepath, os.path.join(assets_dir, "welcome_series/welcome.0")):
                return  # ignore welcome series
        except FileNotFoundError:
            pass

        if self.filetype == "JSON":
            d = self.getDict()
            with open(self.filepath, "w") as f:
                f.write(json.dumps(d, indent=1))
        
        elif self.filetype == "XML":
            self.xml_section.images[0].src = self.src
            self.xml_section.images[0].mag = self.mag
            self.xml_section.thickness = self.thickness
            t = self.tforms["default"]
            xcoef = [t[2], t[0], t[1]]
            ycoef = [t[5], t[3], t[4]]
            xml_tform = XMLTransform(xcoef=xcoef, ycoef=ycoef).inverse
            self.xml_section.images[0].transform = xml_tform
            self.xml_section.contours = []
            for trace in self.tracesAsList():
                self.xml_section.contours.append(trace.getXMLObj(xml_tform))
            write_section(self.xml_section, directory=os.path.dirname(self.filepath), outpath=self.filepath, overwrite=True)
