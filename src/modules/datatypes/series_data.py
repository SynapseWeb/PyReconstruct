from modules.calc import lineDistance, area

from .section import Section
from .transform import Transform
from .trace import Trace

class TraceData():

    def __init__(self, trace : Trace, tform : Transform):
        """Create a trace table item.
        
            Params:
                trace (Trace): the trace object for the trace
                tform (Transform): the transform applied to the trace
                index (int): the index of the trace in the contour
        """
        self.closed = trace.closed
        self.negative = trace.negative
        self.tags = trace.tags
        tformed_points = tform.map(trace.points)
        self.length = lineDistance(tformed_points, closed=trace.closed)
        if not self.closed:
            self.area = 0
        else:
            self.area = area(tformed_points)
            if self.negative: self.area *= -1
        self.radius = trace.getRadius(tform)
    
    def getTags(self):
        return self.tags

    def getLength(self):
        return self.length
    
    def getArea(self):
        return self.area
    
    def getRadius(self):
        return self.radius


class ObjectData():

    def __init__(self):
        """Create an object data object."""
        self.traces = {}
    
    def isEmpty(self):
        """Return True of object data is empty."""
        return bool(self.traces)
    
    def addTrace(self, trace : Trace, section : Section, series):
        """Add a trace to the object data.
        
            Params:
                trace (Trace): the trace to add
                section (Section): the section containing the trace
                series (Series): the series containing the trace
        """
        if section.n not in self.traces.keys():
            self.traces[section.n] = []
        self.traces[section.n].append(TraceData(trace, section.tforms[series.alignment]))
    
    def clearSection(self, snum : int):
        """Clear the traces on a specific section.
        
            Params:
                snum (int): the section number to clear
        """
        self.traces[snum] = []

class SeriesData():

    def __init__(self, series):
        """Create a series data object.
        
            Params:
                series (Series): the series to keep track of data
        """
        self.series = series
        self.data = {
            "sections": {},
            "objects": {},
        }
    
    def __getitem__(self, index):
        """Allow the user to directly index the data dictionary."""
        return self.data[index]
    
    def refresh(self):
        """Completely refresh the series data."""
        self.data = {
            "sections": {},
            "objects": {},
        }
        for snum, section in self.series.enumerateSections():
            self.updateSection(section,update_traces=True)
    
    def updateSection(self, section : Section, update_traces=False, trace_names=[]):
        """Update the existing section data.
        
            Params:
                section (Section): the section with data to update
                series (Series): the series containing the section
                update_traces (bool): True if traces should also be updated
                trace_names (list): list of trace names to update (only used if update_traces is True)
        """
        # create/update the data for a section
        if section.n not in self.data["sections"]:
            d = {
                "thickness": section.thickness,
                "locked": section.align_locked,
                "brightness": section.brightness,
                "contrast": section.contrast,
                "src": section.src,
                "mag": section.mag,
                "tforms": section.tforms,
                "contours": {}
            }
            self.data["sections"][section.n] = d
        else:
            d = self.data["sections"][section.n]
            d["thickness"] = section.thickness
            d["locked"] = section.align_locked
            d["brightness"] = section.brightness
            d["contrast"] = section.contrast
            d["src"] = section.src
            d["mag"] = section.mag
            d["tforms"] = section.tforms
        
        if update_traces:
            # clear existing trace data on this section
            if not trace_names:
                trace_names = self.data["objects"].keys()
            for name in trace_names:
                obj_data = self.data["objects"][name]
                obj_data.clearSection(section.n)
                # add new trace data
                for trace in section.contours[name]:
                    self.addTrace(trace, section)
    
    def addTrace(self, trace : Trace, section : Section):
        """Add trace data to the existing object.
        
            Params:
                trace (Trace): the trace to add
                section (Section): the section containing the trace
            Returns:
                (bool): True if a new object was just created
        """
        # create the section data if not existing already
        if section.n not in self.data:
            self.updateSection(section, update_traces=True)
            # ASSUME TRACE IS ALREADY ON THE SECTION
            return
        
        # create object if not already
        object_data = self.data["objects"]
        if trace.name not in object_data:
            new_object = True
            object_data[trace.name] = ObjectData()
        else:
            new_object = False
        
        object_data[trace.name].addTrace(trace, section, self.series)

        return new_object
    
    def getStart(self, obj_name : str):
        """Get the first section of the object."""
        obj_data = self.data["objects"].get(obj_name)
        if obj_data is None or obj_data.isEmpty():
            return None
        
        return min(obj_data.traces.keys())
        
    def getEnd(self, obj_name : str):
        """Get the last section of the object."""
        obj_data = self.data["objects"].get(obj_name)
        if obj_data is None or obj_data.isEmpty():
            return None
        
        return max(obj_data.traces.keys())
    
    def getCount(self, obj_name : str):
        """Get the number of traces associated with the object."""
        obj_data = self.data["objects"].get(obj_name)
        if obj_data is None:
            return None
        
        c = 0
        for trace_list in obj_data.traces.values():
            c += len(trace_list)
        return c
    
    def getFlatArea(self, obj_name : str):
        """Get the flat area of the object."""
        obj_data = self.data["objects"].get(obj_name)
        if obj_data is None:
            return None
        
        fa = 0
        for snum, trace_list in obj_data.traces.items():
            for trace_data in trace_list:
                if trace_data.closed:
                    fa += trace_data.getArea()
                else:
                    fa += trace_data.getLength() * self.data["sections"][snum]["thickness"]
        return fa

    def getVolume(self, obj_name : str):
        """Get the volume of the object."""
        obj_data = self.data["objects"].get(obj_name)
        if obj_data is None:
            return None
        
        v = 0
        for snum, trace_list in obj_data.traces.items():
            for trace_data in trace_list:
                v += trace_data.getArea() * self.data["sections"][snum]["thickness"]
        return v
    
    def getTags(self, obj_name : str):
        """Get the tags associated with an object."""
        obj_data = self.data["objects"].get(obj_name)
        if obj_data is None:
            return None
        
        tags = set()
        for trace_list in obj_data.trace.values():
            for trace_data in trace_list:
                tags = tags.union(trace_data.getTags())
        return tags

    def getZtraceDist(self, ztrace_name : str):
        """Get the distance of a ztrace."""
        return self.series.ztraces[ztrace_name].getDistance()
    
    def clearSection(self, snum : int):
        """Clear the object data for a speicified section.
        
            Params:
                snum (int): the section number
        """
        for obj_data in self.data["objects"].values():
            obj_data.clearSection(snum)
