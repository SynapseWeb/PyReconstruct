class Ztrace():

    def __init__(self, name : str, points : list = []):
        """Create a new ztrace.
        
            Params:
                name (str): the name of the ztrace
                points (list): the points for the trace (x, y, section)
        """
        self.name = name
        self.points = points
    
    def getDict(self) -> dict:
        """Get a dictionary representation of the object.
        
            Returns:
                (dict): the dictionary representation of the object
        """
        d = {}
        d["name"] = self.name
        d["points"] = self.points.copy()
        return d
    
    def fromDict(d):
        """Create the object from a dictionary.
        
            Params:
                d (dict): the dictionary representation of the object
        """
        ztrace = Ztrace(d["name"])
        ztrace.points = d["points"]
        return ztrace
    
    def smooth(self):
        """Smooth a ztrace."""

