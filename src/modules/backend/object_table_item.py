from modules.calc.quantification import area, lineDistance

class ObjectTableItem():

    def __init__(self, name : str):
        """Create an object table item.
        
            Params:
                name (str): the name of the trace
        """
        self.name = name
        self.data = {}
    
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
    
    def clearSectionData(self, n):
        if n in self.data.keys():
            del self.data[n]
            return True
        else:
            return False
    
    def isEmpty(self):
        return not bool(self.data)
    
    def addTrace(self, trace_points : list, trace_is_closed : bool, section_num : int, section_thickness : float):
        """Add trace data to the existing object.
        
            Params:
                trace_points (list): list of points
                trace_is_closed (bool): whether or not the trace is closed
                section_num (int): the section number the trace is on
                section_thickness (float): the section thickness for the trace
        """
        if section_num not in self.data:
            self.data[section_num] = {}
            self.data[section_num]["count"] = 0
            self.data[section_num]["flat_area"] = 0
            self.data[section_num]["volume"] = 0
        self.data[section_num]["count"] += 1
        trace_distance = lineDistance(trace_points, closed=trace_is_closed)
        if trace_is_closed:
            trace_area = area(trace_points)
            self.data[section_num]["flat_area"] += trace_area
            self.data[section_num]["volume"] += trace_area * section_thickness
        else:
            self.data[section_num]["flat_area"] += trace_distance * section_thickness
    
    def removeTrace(self, trace_points : list, trace_is_closed : bool, section_num : int, section_thickness : float):
        """Remove trace data from the object.
        
            Params:
                trace_points (list): list of points
                trace_is_closed (bool): whether or not the trace is closed
                section_num (int): the section number the trace is on
                section_thickness (float): the section thickness for the trace
        """
        self.data[section_num]["count"] -= 1
        trace_distance = lineDistance(trace_points, closed=trace_is_closed)
        if trace_is_closed:
            trace_area = area(trace_points)
            self.data[section_num]["flat_area"] -= trace_area
            self.data[section_num]["volume"] -= trace_area * section_thickness
        else:
            self.data[section_num]["flat_area"] -= trace_distance * section_thickness
    
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
                combined.data[snum]["count"] = other.data[snum]["count"]
                combined.data[snum]["flat_area"] = other.data[snum]["flat_area"]
                combined.data[snum]["volume"] = other.data[snum]["volume"]
            else:
                for key in combined.data[snum]:
                    combined.data[snum][key] += other.data[snum][key]
        return combined