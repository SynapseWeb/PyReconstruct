import json

class Series():

    def __init__(self, filename):
        """Load the series file"""
        self.filename = filename
        with open(filename, "r") as f:
            series_data = json.load(f)
        
        self.sections = series_data["sections"]
        self.current_section = series_data["current_section"]
        self.window = series_data["window"]
    
    def getDict(self):
        """Convert series object into a dictionary"""
        d = {}
        d["sections"] = self.sections
        d["current_section"] = self.current_section
        d["window"] = self.window
        return d
        
    def save(self):
        """Save file into json"""
        d = self.getDict()
        with open(self.filename, "w") as f:
            f.write(json.dumps(d, indent=2))