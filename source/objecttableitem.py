from quantification import area, lineDistance

class ObjectTableItem():

    def __init__(self, name : str):
        """Create an object table item.
        
            Params:
                name (str): the name of the trace
        """
        self.name = name
        # establish defaults
        self.start = -1
        self.end = -1
        self.count = 0
        self.surface_area = 0
        self.flat_area = 0
        self.volume = 0
    
    def addTrace(self, trace_points : list, trace_is_closed : bool, section_num : int, section_thickness : float):
        """Add trace data to the existing object.
        
            Params:
                trace_points (list): list of points
                trace_is_closed (bool): whether or not the trace is closed
                section_num (int): the section number the trace is on
                section_thickness (float): the section thickness for the trace
        """
        if self.start == -1:
            self.start = section_num
        self.end = max(section_num, self.end)
        self.count += 1
        trace_distance = lineDistance(trace_points, closed=trace_is_closed)
        if trace_is_closed:
            trace_area = area(trace_points)
            self.surface_area += trace_distance * section_thickness
            self.flat_area += trace_area
            self.volume += trace_area * section_thickness
        else:
            self.surface_area += trace_distance * section_thickness * 2
            self.flat_area += trace_distance * section_thickness

