import os
import json
from .trace import Trace

from modules.pyrecon.utils.reconstruct_reader import process_series_file
from modules.pyrecon.utils.reconstruct_writer import write_series

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
            try:
                self.src_dir = series_data["src_dir"]
            except KeyError:
                self.src_dir = ""
            self.window = series_data["window"]
            self.palette_traces = series_data["palette_traces"]
            for i in range(len(self.palette_traces)):
                self.palette_traces[i] = Trace.fromDict(self.palette_traces[i])
            self.current_trace = Trace.fromDict(series_data["current_trace"])
        
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
        return d
        
    def save(self):
        """Save file into json."""
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