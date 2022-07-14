import json
from trace import Trace

class Series():

    def __init__(self, filepath):
        """Load the series file.
        
            Params:
                filepath (str): the filepath for the series JSON file
        """
        self.filepath = filepath
        with open(filepath, "r") as f:
            series_data = json.load(f)
        
        self.sections = {}
        for section_num, section_filename in series_data["sections"].items():
            self.sections[int(section_num)] = section_filename
        self.current_section = series_data["current_section"]
        self.window = series_data["window"]
        self.palette_traces = series_data["palette_traces"]
        for i in range(len(self.palette_traces)):
            self.palette_traces[i] = Trace.fromDict(self.palette_traces[i])
        self.current_trace = Trace.fromDict(series_data["current_trace"])
    
    def getDict(self) -> dict:
        """Convert series object into a dictionary.
        
            Returns:
                (dict) all of the compiled section data
        """
        d = {}
        d["sections"] = self.sections
        d["current_section"] = self.current_section
        d["window"] = self.window
        d["palette_traces"] = []
        for trace in self.palette_traces:
            d["palette_traces"].append(trace.getDict())
        d["current_trace"] = self.current_trace.getDict()
        return d
        
    def save(self):
        """Save file into json."""
        d = self.getDict()
        with open(self.filepath, "w") as f:
            f.write(json.dumps(d, indent=1))