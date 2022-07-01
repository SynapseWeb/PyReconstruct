import json
from trace import Trace

class Section():

    def __init__(self, filename):
        """Load the section file"""
        self.filename = filename
        with open(filename, "r") as f:
            section_data = json.load(f)

        self.src = section_data["src"]
        self.mag = section_data["mag"]
        self.tform = section_data["tform"]
        self.traces = section_data["traces"]
        for i in range(len(self.traces)):  # convert contour dictionaries into Contour objects
            self.traces[i] = Trace.fromDict(self.traces[i])

    def getDict(self):
        """Convert section object into a dictionary"""
        d = {}
        d["src"] = self.src
        d["mag"] = self.mag
        d["tform"] = self.tform
        d["traces"] = self.traces
        for i in range(len(d["traces"])):  # convert Contour objects in contour dictionaries
            d["traces"][i] = d["traces"][i].getDict()
        return d
    
    def save(self):
        """Save file into json"""
        d = self.getDict()
        with open(self.filename, "w") as f:
            f.write(json.dumps(d, indent=2))