from quantification import area, lineDistance

class ObjectTableItem():

    def __init__(self, name):
        self.name = name
        self.start = -1
        self.end = -1
        self.count = 0
        self.surface_area = 0
        self.flat_area = 0
        self.volume = 0
    
    def addTrace(self, trace_points, trace_is_closed, section_num, section_thickness):
        if self.start == -1:
            self.start = section_num
        self.end = max(section_num, self.end)
        self.count += 1
        trace_distance = lineDistance(trace_points)
        if trace_is_closed:
            trace_area = area(trace_points)
            self.surface_area += trace_distance * section_thickness
            self.flat_area += trace_area
            self.volume += trace_area * section_thickness
        else:
            self.surface_area += trace_distance * section_thickness * 2
            self.flat_area += trace_distance * section_thickness

