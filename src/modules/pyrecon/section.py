import os
import json
from modules.pyrecon.contour import Contour
from modules.pyrecon.trace import Trace
from modules.pyrecon.transform import Transform

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
        self.added_traces = []
        self.removed_traces = []

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

            self.tforms = {}
            for a in section_data["tforms"]:
                self.tforms[a] = Transform(section_data["tforms"][a])
            
            self.thickness = section_data["thickness"]
            self.contours = section_data["contours"]
            for name in self.contours:
                self.contours[name] = Contour(
                    name,
                    [Trace.fromDict(t, name) for t in self.contours[name]]  # convert trace dictionaries into trace objects
                )
        
        elif self.filetype == "XML":
            self.xml_section = process_section_file(filepath)
            image = self.xml_section.images[0] # assume only one image
            self.tforms = {}
            self.tforms["default"] = Transform(
                list(image.transform.tform()[:2,:].reshape(6))
            )
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
        # # insert username as first tag
        # trace.tags = set((os.getlogin(),)).union(trace.tags)

        if trace.name in self.contours:
            self.contours[trace.name].append(trace)
        else:
            self.contours[trace.name] = Contour(trace.name, [trace])
        
        self.added_traces.append(trace)
    
    def removeTrace(self, trace : Trace):
        """Remove a trace from the trace dictionary.
        
            Params:
                trace (Trace): the trace to remove from the traces dictionary
        """
        if trace.name in self.contours:
            self.contours[trace.name].remove(trace)
            self.removed_traces.append(trace)
    
    def clearTracking(self):
        """Clear the added_traces and removed_traces lists."""
        self.added_traces = []
        self.removed_traces = []
    
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

        # save tforms
        d["tforms"] = {}
        for a in self.tforms:
            d["tforms"][a] = self.tforms[a].getList()

        d["thickness"] = self.thickness

        # save contours
        d["contours"] = {}
        for contour_name in self.contours:
            if not self.contours[contour_name].isEmpty():
                d["contours"][contour_name] = [
                    trace.getDict(include_name=False) for trace in self.contours[contour_name]
                ]
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
        section_data["tforms"]["default"]= Transform([1, 0, 0, 0, 1, 0]) # identity matrix default
        section_data["contours"] = {}
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
            t = self.tforms["default"].getList()
            xcoef = [t[2], t[0], t[1]]
            ycoef = [t[5], t[3], t[4]]
            xml_tform = XMLTransform(xcoef=xcoef, ycoef=ycoef).inverse
            self.xml_section.images[0].transform = xml_tform
            self.xml_section.contours = []
            for trace in self.tracesAsList():
                self.xml_section.contours.append(trace.getXMLObj(xml_tform))
            write_section(self.xml_section, directory=os.path.dirname(self.filepath), outpath=self.filepath, overwrite=True)
