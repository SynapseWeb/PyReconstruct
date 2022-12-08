import os
import json
from modules.pyrecon.contour import Contour
from modules.pyrecon.trace import Trace
from modules.pyrecon.transform import Transform

from constants.locations import assets_dir

class Section():

    def __init__(self, filepath : str):
        """Load the section file.
        
            Params:
                filepath (str): the file path for the section JSON file
        """
        self.filepath = filepath
        self.added_traces = []
        self.removed_traces = []
        self.modified_traces = []

        try:
            with open(filepath, "r") as f:
                section_data = json.load(f)
        except json.decoder.JSONDecodeError:
            print("Invalid JSON file")
            raise json.decoder.JSONDecodeError
        
        self.src = section_data["src"]
        self.brightness = section_data["brightness"]
        self.contrast = section_data["contrast"]
        self.mag = section_data["mag"]
        self.align_locked = section_data["align_locked"]

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
    
    def addTrace(self, trace : Trace, log_message=None):
        """Add a trace to the trace dictionary.
        
            Params:
                trace (Trace): the trace to add
                log_message (str): the history log message to put on the trace
        """
        # add to the trace history
        if log_message:
            trace.addLog(log_message)
        else:
            if trace.isNew():
                trace.addLog("created")
            else:
                trace.addLog("modified")

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
    
    def setAlignLocked(self, align_locked : bool):
        """Set the alignment locked status of the section.
        
            Params:
                align_locked (bool): the new locked status
        """
        self.align_locked = align_locked
    
    def clearTracking(self):
        """Clear the added_traces and removed_traces lists."""
        self.added_traces = []
        self.removed_traces = []
        self.modified_traces = []
    
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
        d["align_locked"] = self.align_locked

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
        section_data["align_locked"] = True
        section_data["thickness"] = thickness  # section thickness
        section_data["tforms"] = {}  
        section_data["tforms"]["default"]= [1, 0, 0, 0, 1, 0] # identity matrix default
        section_data["contours"] = {}
        section_fp = os.path.join(wdir, series_name + "." + str(snum))
        with open(section_fp, "w") as section_file:
            section_file.write(json.dumps(section_data, indent=2))
        return Section(section_fp)
   
    def save(self):
        """Save file into json."""
        try:
            if os.path.samefile(self.filepath, os.path.join(assets_dir, "welcome_series", "welcome.0")):
                return  # ignore welcome series
        except FileNotFoundError:
            pass
    
        d = self.getDict()
        with open(self.filepath, "w") as f:
            f.write(json.dumps(d, indent=1))
