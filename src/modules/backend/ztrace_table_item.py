from modules.pyrecon.series import Series
from modules.pyrecon.ztrace import Ztrace
from modules.pyrecon.transform import Transform

class ZtraceTableItem():

    def __init__(self, ztrace : Ztrace, series : Series):
        """Create a ztrace table item.
        
            Params:
                ztrace (Ztrace): the ztrace object
                tforms (dict): the transforms for each section number
                section_heights (dict): the z-height of each section number
        """
        # calculate the distance of the ztrace
        self.ztrace = ztrace
        self.name = ztrace.name
        self.dist = ztrace.getDistance(series)
    
    def getDist(self):
        return self.dist

