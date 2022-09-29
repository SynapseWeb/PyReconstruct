import os
import json
from .trace import Trace

from modules.pyrecon.classes.transform import Transform as XMLTransform
from modules.pyrecon.utils.reconstruct_reader import process_section_file
from modules.pyrecon.utils.reconstruct_writer import write_section

from constants.locations import assets_dir

class Section():

    def __init__(self, filepath : str):
        """Load the section file.
        
            Params:
                filepath (str): the file path for the section JSON or XML file
        """
        self.filepath = filepath
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
            self.tform = section_data["tform"]
            self.thickness = section_data["thickness"]
            self.traces = section_data["traces"]
            for i in range(len(self.traces)):  # convert trace dictionaries into trace objects
                self.traces[i] = Trace.fromDict(self.traces[i])
        
        elif self.filetype == "XML":
            self.xml_section = process_section_file(filepath)
            image = self.xml_section.images[0] # assume only one image
            tform = list(image.transform.tform()[:2,:].reshape(6))
            self.src = image.src
            self.brightness = 0
            self.contrast = 0
            self.mag = image.mag
            self.thickness = self.xml_section.thickness
            self.tform = tform
            self.traces = []
            for xml_contour in self.xml_section.contours:
                self.traces.append(Trace.fromXMLObj(xml_contour, image.transform))

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
        d["tform"] = self.tform
        d["thickness"] = self.thickness
        d["traces"] = self.traces.copy()
        for i in range(len(d["traces"])):  # convert trace objects in trace dictionaries
            d["traces"][i] = d["traces"][i].getDict()
        return d
    
    def save(self):
        """Save file into json or xml."""
        if self.filepath == assets_dir + "/welcome_series/welcome.0":
            return  # ignore welcome series

        if self.filetype == "JSON":
            d = self.getDict()
            with open(self.filepath, "w") as f:
                f.write(json.dumps(d, indent=1))
        
        elif self.filetype == "XML":
            self.xml_section.images[0].src = self.src
            self.xml_section.images[0].mag = self.mag
            self.xml_section.thickness = self.thickness
            t = self.tform
            xcoef = [t[2], t[0], t[1]]
            ycoef = [t[5], t[3], t[4]]
            xml_tform = XMLTransform(xcoef=xcoef, ycoef=ycoef).inverse
            self.xml_section.images[0].transform = xml_tform
            self.xml_section.contours = []
            for trace in self.traces:
                self.xml_section.contours.append(trace.getXMLObj(xml_tform))
            write_section(self.xml_section, directory=os.path.dirname(self.filepath), outpath=self.filepath, overwrite=True)
