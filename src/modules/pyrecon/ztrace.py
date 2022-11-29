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
    
    def smooth(self, smooth=10):
        """Smooth a ztrace."""

        x = [None] * smooth
        y = [None] * smooth

        points = [[p[0], p[1]] for p in self.points]

        pt_idx = 0
        p = points[pt_idx]

        for i in range(int(smooth/2) + 1):
            
             x[i] = p[0]
             y[i] = p[1]
        
        q = p
    
        for i in range(int(smooth/2) + 1, smooth):
        
            x[i] = q[0]
            y[i] = q[1]
            
            pt_idx += 1
            q = points[pt_idx]
        
        xMA = 0
        yMA = 0

        for i in range(smooth):
            
            xMA += x[i]/smooth
            yMA += y[i]/smooth
        
        for i, point in enumerate(points):  # Loop over all points
        
            point[0] = round(xMA, 4)
            point[1] = round(yMA, 4)
        
            old_x = x[0]
            old_y = y[0]
        
            for i in range(smooth - 1):
                x[i] = x[i+1]
                y[i] = y[i+1]
        
            try:
                pt_idx += 1
                q = points[pt_idx]
                x[smooth - 1] = q[0]
                y[smooth - 1] = q[1]
        
            except:
                pass
                
            xMA += (x[smooth-1] - old_x) / smooth
            yMA += (y[smooth-1] - old_y) / smooth

        # Update self.points
        for i, p in enumerate(points):
            save_point_old = self.points[i]
            current_sec = self.points[i][2]
            self.points[i] = (p[0], p[1], current_sec)
            print(f'old: {save_point_old} new: {self.points[i]}')

        return None
