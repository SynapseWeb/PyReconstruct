class VolItem():

    def __init__(self, name : str, gl_item, volume : float):
        """Create the volume item.
        
            Params:
                name (str): the name of the item
                gl_item: the opengl item
                volume (float): the volume of the object
        """
        self.name = name
        self.gl_item = gl_item
        self.volume = volume

    def isZtrace(self):
        """Returns if item is a ztrace."""
        return self.volume == 0
    
    def __gt__(self, other):
        return self.volume > other.volume
    
    def __lt__(self, other):
        return self.volume < other.volume