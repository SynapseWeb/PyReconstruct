"""Collect data to pass to table manager."""
from typing import Union

from PyReconstruct.modules.calc import lineDistance, area

from .section import Section
from .transform import Transform
from .trace import Trace


class TraceData():

    def __init__(self, trace : Trace, index : int, tform : Transform):
        """Create a trace table item.
        
            Params:
                trace (Trace): the trace object for the trace
                tform (Transform): the transform applied to the trace
        """
        self.index = index
        self.closed = trace.closed
        self.hidden = trace.hidden
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
        self.centroid = trace.getCentroid(tform)
        self.feret = trace.getFeret(tform)
    
    def getTags(self):
        return self.tags

    def getLength(self):
        return self.length
    
    def getArea(self):
        return self.area
    
    def getRadius(self):
        return self.radius

    def getCentroid(self):
        return self.centroid

    def getFeret(self):
        return self.feret

    def __lt__(self, other):
        return self.index < other.index


class ObjectData():

    def __init__(self):
        """Create an object data object."""
        self.traces = {}
    
    def isEmpty(self) -> bool:
        """Return True of object data is empty."""
        return not bool(self.traces)
    
    def addTrace(self, trace : Trace, section : Section, series):
        """Add a trace to the object data.
        
            Params:
                trace (Trace): the trace to add
                section (Section): the section containing the trace
                series (Series): the series containing the trace
        """
        if section.n not in self.traces:
            self.traces[section.n] = []
            
        alignment = series.getAttr(trace.name, "alignment")
        
        if alignment is None:
            
            alignment = series.alignment
            
        elif alignment not in section.tforms:
            
            series.setAttr(trace.name, "alignment", None)
            alignment = series.alignment

        tform = section.tforms[alignment]

        i = len(self.traces[section.n])
        
        self.traces[section.n].append(
            TraceData(trace, i, tform)
        )
    
    def clearSection(self, snum : int):
        """Clear the traces on a specific section.
        
            Params:
                snum (int): the section number to clear
        """
        if snum in self.traces:
            del(self.traces[snum])


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
        self.supress_logging = False
    
    def __getitem__(self, index):
        """Allow direct indexing of data dictionary."""
        return self.data[index]

    @property
    def objects(self):
        """Return all object data."""

        return self.data["objects"]

    @property
    def traces(self):
        """Return all trace data by object."""

        trace_data = {}

        for obj_name, obj_data in self.objects.items():

            trace_data[obj_name] = obj_data.traces

        return trace_data
    
    def refresh(self):
        """Completely refresh the series data."""

        self.data = {
            "sections": {},
            "objects": {},
        }

        for snum, section in self.series.enumerateSections():

            self.updateSection(section, update_traces=True, log_events=False)
    
    def updateSection(self, section : Section, update_traces=False, all_traces=True, log_events=True):
        """Update the existing section data.
        
            Params:
                section (Section): the section with data to update
                update_traces (bool): True if all traces should also be updated
                all_traces (bool): True if all traces on the section should be updated IF NO TRACES HAVE BEEN MARKED AS MODIFIED
                log_events (bool): True if events (creating and deleting objects) should be logged
        """
        # create/update the data for a section
        if section.n not in self.data["sections"]:
            
            d = {
                "thickness": section.thickness,
                "calgrid": section.calgrid,
                "locked": section.align_locked,
                "bc_profiles": section.bc_profiles.copy(),
                "src": section.src,
                "mag": section.mag,
                "flags": [f.copy() for f in section.flags],
                "tforms": section.tforms.copy()
            }
            
            self.data["sections"][section.n] = d
            
        else:
            
            d = self.data["sections"][section.n]
            d["thickness"] = section.thickness
            d["locked"] = section.align_locked
            d["bc_profiles"] = section.bc_profiles.copy()
            d["src"] = section.src
            d["mag"] = section.mag
            d["flags"] = [f.copy() for f in section.flags]
            d["tforms"] = section.tforms.copy()
        
        if update_traces:
            
            ## Check if there are specific traces to be updated
            trace_names = section.getAllModifiedNames()

            if section.tformsModified(scaling_only=True) or (all_traces and not trace_names):
                trace_names = section.contours.keys()

            ## Keep track of objects that are newly created/destroyed
            added_objects = set()
            removed_objects = set()

            ## Clear existing trace data on this section
            for name in trace_names:
                
                ## Check if object is new
                if name in self.data["objects"]:
                    self.data["objects"][name].clearSection(section.n)
                    
                ## Add new trace data
                if name in section.contours:
                    for trace in section.contours[name]:
                        is_new_object = self.addTrace(trace, section)
                        if is_new_object:
                            added_objects.add(name)
            
            ## Check for removed objects
            for name in trace_names:
                if name in self.data["objects"]:
                    obj_data = self.data["objects"][name]
                    if obj_data.isEmpty():
                        del(self.data["objects"][name])
                        removed_objects.add(name)
            
            ## Log newly created/destroyed objects
            if log_events and not self.supress_logging:
                
                for obj_name in added_objects:
                    
                    self.series.addLog(obj_name, None, "Create object")
                    ## Set the fixed alignment of the object to creation
                    self.series.setAttr(obj_name, "alignment", self.series.alignment)
                    
                for obj_name in removed_objects:
                    
                    self.series.addLog(obj_name, None, "Delete object")
                    ## Remove object from object attributes dicts
                    self.series.removeObjAttrs(obj_name)
    
    def addTrace(self, trace : Trace, section : Section):
        """Add trace data to the existing object.
        
            Params:
                trace (Trace): the trace to add
                section (Section): the section containing the trace
            Returns:
                (bool): True if a new object was just created
        """
        ## Create section data if not present
        if section.n not in self.data["sections"]:
            
            self.updateSection(section, update_traces=True)
            return ## Assume trace already on section
        
        ## Create object if not present
        object_data = self.data["objects"]

        if trace.name not in object_data:

            new_object = True
            object_data[trace.name] = ObjectData()

        else:

            new_object = False
        
        object_data[trace.name].addTrace(trace, section, self.series)

        return new_object
    
    def getStart(self, obj_name : str) -> int:
        """Get the first section of the object.
        
            Params:
                obj_name (str): the name of the object to retrieve data for
        """
        obj_data = self.data["objects"].get(obj_name)
        if obj_data is None or obj_data.isEmpty():
            return None
        
        return min(obj_data.traces.keys())
        
    def getEnd(self, obj_name : str) -> int:
        """Get the last section of the object.
        
            Params:
                obj_name (str): the name of the object to retrieve data for
        """
        obj_data = self.data["objects"].get(obj_name)
        if obj_data is None or obj_data.isEmpty():
            return None
        
        return max(obj_data.traces.keys())
    
    def getCount(self, obj_name : str) -> int:
        """Get the number of traces associated with the object.
        
            Params:
                obj_name (str): the name of the object to retrieve data for
        """
        obj_data = self.data["objects"].get(obj_name)
        if obj_data is None:
            return None
        
        c = 0
        for trace_list in obj_data.traces.values():
            c += len(trace_list)
        return c
    
    def getFlatArea(self, obj_name : str) -> float:
        """Get the flat area of the object.
        
            Params:
                obj_name (str): the name of the object to retrieve data for
        """
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

    def getVolume(self, obj_name : str) -> float:
        """Get the volume of the object.
        
            Params:
                obj_name (str): the name of the object to retrieve data for
        """
        obj_data = self.data["objects"].get(obj_name)

        if obj_data is None:
            return None
        
        v = 0
        
        for snum, trace_list in obj_data.traces.items():
            
            for trace_data in trace_list:
                v += trace_data.getArea() * self.data["sections"][snum]["thickness"]
                
        return v

    def getConfiguration(self, obj_name: str) -> Union[str, None]:
        """Get the configuration of the object.

            Params:
                obj_name (str): the name of the object to retrieve data for
        """
        obj_data = self.data["objects"].get(obj_name)

        if obj_data is None:
            return None

        closed = []
        
        for _, trace_list in obj_data.traces.items():

            for trace_data in trace_list:
                closed.append(trace_data.closed)

        if sum(closed) == 0:
            config = "open"
            
        elif sum(closed) == len(closed):
            config = "closed"
            
        else:
            config = "mixed"

        return config
    
    def getTags(self, obj_name : str) -> set:
        """Get the tags associated with an object.
        
            Params:
                obj_name (str): the name of the object to retrieve data for
        """
        obj_data = self.data["objects"].get(obj_name)
        if obj_data is None:
            return None
        
        tags = set()
        for trace_list in obj_data.traces.values():
            for trace_data in trace_list:
                tags = tags.union(trace_data.getTags())
        return tags
    
    def getAvgRadius(self, obj_name : str) -> float:
        """Get the average stamp radius of an object.
        
            Params:
                obj_name (str): the name of the object to retrieve data for
        """
        obj_data = self.data["objects"].get(obj_name)
        if obj_data is None:
            return None
        
        radii = []
        for trace_list in obj_data.traces.values():
            for trace_data in trace_list:
                radii.append(trace_data.getRadius())
        avg_radius = sum(radii) / len(radii)

        return avg_radius

    def getZtraceDist(self, ztrace_name : str) -> float:
        """Get the distance of a ztrace.
        
            Params:
                ztrace_name (str): the name of the ztrace to retrieve data for
        """
        return self.series.ztraces[ztrace_name].getDistance(self.series)

    def getZtraceStart(self, ztrace_name : str) -> int:
        """Get the first section of a ztrace.
        
            Params:
                ztrace_name (str): the name of the ztrace to retrieve data for
        """
        return self.series.ztraces[ztrace_name].getStart()
    
    def getZtraceEnd(self, ztrace_name : str) -> int:
        """Get the last section of a ztrace.
        
            Params:
                ztrace_name (str): the name of the ztrace to retrieve data for
        """
        return self.series.ztraces[ztrace_name].getEnd()
    
    def clearSection(self, snum : int):
        """Clear the object data for a speicified section.
        
            Params:
                snum (int): the section number
        """
        for obj_data in self.data["objects"].values():
            obj_data.clearSection(snum)
        
    def getTraceData(self, name : str, snum : int) -> list:
        """Get the list of trace data objects.
        
            Params:
                name (str): the name of the object/trace
                snum (int): the section number
            Returns:
                (list): the list of TraceData objects
        """
        if name in self.data["objects"] and snum in self.data["objects"][name].traces:
            return self.data["objects"][name].traces[snum]
        return None

    def getFlagCount(self) -> int:
        """Get the number of flags in the series."""
        c = 0
        for data in self.data["sections"].values():
            c += len(data["flags"])
        return c
    
    def exportTracesCSV(self, out_fp : str = None):
        """Export all trace data to a CSV file.
        
            Params:
                out_fp (str): filepath of exported CSV (str returned if no filepath provided)
        """
        out_str = "Name,Section,Index,Hidden,Closed,Tags,Length,Area,Radius,Centroid-x,Centroid-y,Feret-Max,Feret-Min\n"

        ## Iterate through all traces
        objs = self.data["objects"].keys()
        
        for name in sorted(objs):
            
            sections = self.series.sections.keys()
            
            for snum in sorted(sections):
                
                trace_list = self.getTraceData(name, snum)
                
                if not trace_list:
                    
                    continue
                
                for i, t in enumerate(trace_list):

                    hidden     = "yes" if t.hidden else "no"
                    closed     = "yes" if t.closed else "no"
                    tags       = ' '.join(t.getTags())
                    length     = round(t.getLength(), 7)
                    xs_area    = round(t.getArea(), 7)
                    radius     = round(t.getRadius(), 7)

                    centroid   = t.getCentroid()
                    centroid_x = round(centroid[0], 7)
                    centroid_y = round(centroid[1], 7)

                    feret      = t.getFeret()
                    feret_max  = round(feret[1], 7)
                    feret_min  = round(feret[0], 7)

                    vals = [
                        name,
                        snum,
                        i,
                        hidden,
                        closed,
                        tags,
                        length,
                        xs_area,
                        radius,
                        centroid_x,
                        centroid_y,
                        feret_max,
                        feret_min
                    ]

                    vals = list(map(str, vals))
                    
                    trace_line = ','.join(vals)
                    out_str += trace_line + "\n"
        
        # export the csv file
        if out_fp:
            with open(out_fp, "w") as f:
                f.write(out_str)
        else:
            return out_str
    
    def getAvgMag(self):
        """Return the average magnification of the series."""
        mags = []
        for sdata in self.data["sections"].values():
            mags.append(sdata["mag"])
        return sum(mags) / len(mags)

    def getAvgThickness(self):
        """Return the average thickness of the series."""
        thicknesses = []
        for sdata in self.data["sections"].values():
            thicknesses.append(sdata["thickness"])
        return sum(thicknesses) / len(thicknesses)

    
