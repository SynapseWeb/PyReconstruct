import json
from trace import Trace

class Section():

    def __init__(self, filepath : str):
        """Load the section file.
        
            Params:
                filepath (str): the file path for the section JSON file
        """
        self.filepath = filepath
        with open(filepath, "r") as f:
            section_data = json.load(f)
        self.src = section_data["src"]
        self.mag = section_data["mag"]
        self.thickness = section_data["thickness"]
        self.tform = section_data["tform"]
        self.traces = section_data["traces"]
        for i in range(len(self.traces)):  # convert contour dictionaries into Contour objects
            self.traces[i] = Trace.fromDict(self.traces[i])

    def getDict(self) -> dict:
        """Convert section object into a dictionary.
        
            Returns:
                (dict) all of the compiled section data
        """
        d = {}
        d["src"] = self.src
        d["mag"] = self.mag
        d["thickness"] = self.thickness
        d["tform"] = self.tform
        d["traces"] = self.traces.copy()
        for i in range(len(d["traces"])):  # convert Contour objects in contour dictionaries
            d["traces"][i] = d["traces"][i].getDict()
        return d
    
    def save(self):
        """Save file into json."""
        d = self.getDict()
        with open(self.filepath, "w") as f:
            f.write(json.dumps(d, indent=1))