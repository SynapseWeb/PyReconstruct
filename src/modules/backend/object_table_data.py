from PySide6.QtGui import QTransform

from modules.calc.quantification import area, lineDistance

from modules.pyrecon.section import Section

class ObjectTableItem():

    def __init__(self, name : str):
        """Create an object table item.
        
            Params:
                name (str): the name of the trace
        """
        self.name = name
        self.data = {}
    
    def getStart(self):
        return min(list(self.data.keys()))
    
    def getEnd(self):
        return max(list(self.data.keys()))
    
    def getCount(self):
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
        if section_num not in self.data.keys():
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

def loadSeriesData(series, progbar):
    """Load all of the data for each object in the series.
    
        Params:
            progbar (QPorgressDialog): progress bar to update as function progresses
    """
    objdict = {}  # object name : ObjectTableItem (contains data on object)
    prog_value = 0
    final_value = len(series.sections)
    for section_num in series.sections:
        section = series.loadSection(section_num)
        t = section.tform
        point_tform = QTransform(t[0], t[3], t[1], t[4], t[2], t[5])
        for trace in section.traces:
            points = trace.points.copy()
            for i in range(len(points)):
                points[i] = point_tform.map(*points[i])  # transform the points to get accurate data
            if trace.name not in objdict:
                objdict[trace.name] = ObjectTableItem(trace.name)  # create new object if not already exists
            objdict[trace.name].addTrace(points, trace.closed, section_num, section.thickness)
        prog_value += 1
        progbar.setValue(prog_value / final_value * 100)
        if progbar.wasCanceled(): return
    
    return objdict

def getObjectsToUpdate(objdict : dict, section_num : int, section : Section):
    objects_to_update = set()
    for name, item in objdict.items():
        had_existing_data = item.clearSectionData(section_num)
        if had_existing_data:
            objects_to_update.add(name)
    
    t = section.tform
    point_tform = QTransform(t[0], t[3], t[1], t[4], t[2], t[5])
    section_thickness = section.thickness
    for trace in section.traces:
        name = trace.name
        closed = trace.closed
        points = trace.points.copy()
        for i in range(len(points)):
            points[i] = point_tform.map(*points[i])  # transform the points to get accurate data
        if name not in objdict:
            objdict[name] = ObjectTableItem(name)  # create new object if not already exists
        objdict[name].addTrace(points, closed, section_num, section_thickness)
        objects_to_update.add(name)
    
    return objects_to_update

