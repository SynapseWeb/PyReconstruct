from modules.pyrecon.ztrace import Ztrace
from modules.pyrecon.transform import Transform

class ZtraceTableItem():

    def __init__(self, ztrace : Ztrace, tforms : dict[Transform], section_heights : dict[float]):
        """Create a ztrace table item.
        
            Params:
                ztrace (Ztrace): the ztrace object
                tforms (dict): the transforms for each section number
                section_heights (dict): the z-height of each section number
        """
        # calculate the distance of the ztrace
        self.ztrace = ztrace
        self.name = ztrace.name
        self.dist = 0
        # establish the first point
        s1 = ztrace.points[0][2]
        x1, y1 = tforms[s1].map(*ztrace.points[0][:2])
        z1 = section_heights[s1]
        for i in range(len(ztrace.points[1:])):
            s2 = ztrace.points[i][2]
            x2, y2 = tforms[s2].map(*ztrace.points[i][:2])
            z2 = section_heights[s2]
            self.dist += ((x2-x1)**2 + (y2-y1)**2 + (z2-z1)**2)**(0.5)
            x1, y1, z1 = x2, y2, z2
    
    def getDist(self):
        return self.dist

