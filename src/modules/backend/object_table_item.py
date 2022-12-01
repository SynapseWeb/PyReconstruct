from modules.calc.quantification import area, lineDistance

from modules.pyrecon.trace import Trace
from modules.pyrecon.transform import Transform

class ObjectTableItem():

    def __init__(self, name : str):
        """Create an object table item (each item represents a row).
        
            Params:
                name (str): the name of the trace
        """
        self.name = name
        self.data = {}
    
    def addTrace(self, trace : Trace, tform : Transform, section_num : int, section_thickness : float):
        """Add trace data to the existing object.
        
            Params:
                trace (Trace): the trace to add
                tform (Transform): the transform applied to the trace
                section_num (int): the section number the trace is on
                section_thickness (float): the section thickness for the trace
        """
        # create the section number data if not existing
        if section_num not in self.data:
            self.data[section_num] = {}
            self.data[section_num]["count"] = 0
            self.data[section_num]["flat_area"] = 0
            self.data[section_num]["volume"] = 0
            self.data[section_num]["tags"] = set()
        
        # add to count
        self.data[section_num]["count"] += 1

        # add the tag to the set
        self.data[section_num]["tags"] = self.data[section_num]["tags"].union(trace.tags)

        # transform the points
        trace_points = tform.map(trace.points)

        # calculate totals to add
        trace_distance = lineDistance(trace_points, closed=trace.closed)
        if trace.closed:
            # subtract from flat area and volume if trace is negative
            if trace.negative:
                coef = -1
            else:
                coef = 1
            trace_area = area(trace_points)
            self.data[section_num]["flat_area"] += trace_area * coef
            self.data[section_num]["volume"] += trace_area * section_thickness * coef
        else:
            self.data[section_num]["flat_area"] += trace_distance * section_thickness
    
    def getStart(self):
        if self.isEmpty():
            return None
        return min(list(self.data.keys()))
    
    def getEnd(self):
        if self.isEmpty():
            return None
        return max(list(self.data.keys()))
    
    def getCount(self):
        if self.isEmpty():
            return None
        c = 0
        for n in self.data:
            c += self.data[n]["count"]
        return c
    
    def getFlatArea(self):
        fa = 0
        for n in self.data:
            fa += self.data[n]["flat_area"]
        return fa
    
    def getVolume(self):
        v = 0
        for n in self.data:
            v += self.data[n]["volume"]
        return v
    
    def getTags(self):
        tags = set()
        for n in self.data:
            tags = tags.union(self.data[n]["tags"])
        return tags
    
    def addTag(self, tag, n):
        self.data[n]["tags"].add(tag)
    
    def removeTag(self, tag, n):
        if tag in self.data[n]["tags"]:
            self.data[n]["tags"].remove(tag)
    
    def clearTags(self):
        for n in self.data:
            self.data[n]["tags"] = set()
    
    def clearSectionData(self, n : int):
        """Clear the object data for a speicified section.
        
            Params:
                n (int): the section number
        """
        if n in self.data.keys():
            del self.data[n]
            return True
        else:
            return False
        
    def clearAllData(self):
        self.data = {}
    
    def isEmpty(self):
        return not bool(self.data)
    
    def combine(self, other):
        """Combine two table data objects.
        
            Params:
                other (ObjectTableItem): the other object to add
            Returns:
                (ObjectTableItem): the sum of the two table items
        """
        # use the name of self
        combined = ObjectTableItem(self.name)
        combined.data = self.data.copy()
        # iterate through all data in other object
        for snum in other.data:
            if snum not in combined.data:
                combined.data[snum] = {}
                for key in combined.data[snum]:
                    combined.data[snum][key] = other.data[snum][key]
            else:
                for key in combined.data[snum]:
                    if type(combined.data[snum][key]) is set:
                        combined.data[snum][key] = combined.data[snum][key].union(other.data[snum][key])
                    else:
                        combined.data[snum][key] += other.data[snum][key]
        return combined
    
    def copy(self, new_name=None):
        """Create a copy of the object table item object.
        
            Params:
                new_name (str): the new name for the copy
        """
        if new_name is None:
            new_oti = ObjectTableItem(self.name)
        else:
            new_oti = ObjectTableItem(new_name)
        new_oti.data = self.data.copy()
        return new_oti