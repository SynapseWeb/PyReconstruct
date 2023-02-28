from modules.legacy_recon.classes.zcontour import ZContour as XMLZContour

from modules.calc.quantification import distance3D

class Ztrace():

    def __init__(self, name : str, color : tuple, points : list = []):
        """Create a new ztrace.
        
            Params:
                name (str): the name of the ztrace
                color (tuple): the display color of the ztrace
                points (list): the points for the trace (x, y, section)
        """
        self.name = name
        self.color = color
        self.points = points
    
    def copy(self):
        """Return a copy of the ztrace object."""
        return Ztrace(
            self.name,
            self.color,
            self.points.copy()
        )

    def overlaps(self, other):
        """Check if the ztraces have the same set of points."""
        for (x1, y1, s1), (x2, y2, s2) in zip(self.points, other.points):
            if s1 != s2 or abs(x1-x2) > 1e-6 or abs(y1-y2) > 1e-6:
                return False
        
        return True
    
    def getDict(self) -> dict:
        """Get a dictionary representation of the object.
        
            Returns:
                (dict): the dictionary representation of the object
        """
        d = {}
        d["color"] = self.color
        d["points"] = self.points.copy()
        return d
    
    # STATIC METHOD
    def dictFromXMLObj(xml_ztrace : XMLZContour):
        """Create a trace from an xml contour object.
        
            Params:
                xml_trace (XMLContour): the xml contour object
                xml_image_tform (XMLTransform): the xml image transform object
            Returns:
                (Trace) the trace object
        """
        # get basic attributes
        name = xml_ztrace.name
        color = list(xml_ztrace.border)
        for i in range(len(color)):
            color[i] = int(color[i] * 255)
        new_ztrace = Ztrace(name, color)
        new_ztrace.points = xml_ztrace.points.copy()
        
        return new_ztrace.getDict()

    def getXMLObj(self, series):
        """Convert the ztrace into an XML object.
        
            Params:
                series (Series): the series containing the ztrace
            Returns:
                (XMLZContour): the XML zcontour object
        """
        tform_pts = []
        for x, y, snum in self.points:
            tform = series.section_tforms[snum][series.alignment]
            pt = (*tform.map(x, y), snum)
            tform_pts.append(pt)
        
        color = [c/255 for c in self.color]

        xml_zcontour = XMLZContour(
            name = self.name,
            closed = False,
            mode = 11,
            border = color,
            fill = color,
            points = tform_pts,
        )

        return xml_zcontour
        
    # STATIC METHOD
    def fromDict(name, d):
        """Create the object from a dictionary.
        
            Params:
                d (dict): the dictionary representation of the object
        """
        ztrace = Ztrace(name, d["color"], d["points"])
        return ztrace
    
    def getSectionData(self, series, section):
        """Get all the ztrace points on a section.
        
            Params:
                series (Series): the series object
                section (Section): the main section object
            Returns:
                (list): list of points
                (list): list of lines between points
        """
        # transform all points to field coordinates
        tformed_pts = []
        for pt in self.points:
            x, y, snum = pt
            if pt[2] == section.n:
                tform = section.tforms[series.alignment]
            else:
                tform = series.section_tforms[pt[2]][series.alignment]
            x, y = tform.map(x, y)
            tformed_pts.append((x, y, snum))
        
        pts = []
        lines = []
        for i, pt in enumerate(tformed_pts):
            # add point to list if on section
            if pt[2] == section.n:
                pts.append(pt[:2])
            
            # check for lines to draw
            if i > 0:
                prev_pt = tformed_pts[i-1]
                if prev_pt[2] <= pt[2]:
                    p1, p2 = prev_pt, pt
                else:
                    p2, p1 = prev_pt, pt 
                if p1[2] <= section.n <= p2[2]:
                    segments = p2[2] - p1[2] + 1
                    x_inc = (p2[0] - p1[0]) / segments
                    y_inc = (p2[1] - p1[1]) / segments
                    segment_i = section.n - p1[2]
                    lines.append((
                        (
                            p1[0] + segment_i*x_inc,
                            p1[1] + segment_i*y_inc
                        ),
                        (
                            p1[0] + (segment_i+1)*x_inc,
                            p1[1] + (segment_i+1)*y_inc
                        )
                    ))
        
        return pts, lines

    def getDistance(self, series):
        """Get the distance of the z-trace.
        
            Params:
                series (Series): the series containing the ztrace
            Returns:
                (float): the distance of the ztrace
        """
        # get z-values for each section
        zvals = series.getZValues()

        real_pts = []
        for x, y, snum in self.points:
            tform = series.section_tforms[snum][series.alignment]
            new_pt = (*tform.map(x, y), zvals[snum])
            real_pts.append(new_pt)
        
        dist = 0
        for i in range(len(real_pts[:-1])):
            x1, y1, z1 = real_pts[i]
            x2, y2, z2 = real_pts[i+1]
            dist += distance3D(x1, y1, z1, x2, y2, z2)

        return dist   

    def smooth(self, series, smooth=10):
        """Smooth z-trace (based on legacy Reconstruct algorithm).
        
            Params:
                series (Series): the series object (contains transform data)
                smooth (int): the smoothing factor
        """
        # transform the points
        points = []
        for pt in self.points:
            x, y, snum = pt
            tform = series.section_tforms[snum][series.alignment]
            x, y = tform.map(x, y)
            points.append([x, y, snum])
        
        x = [None] * smooth
        y = [None] * smooth

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
        
        # reverse-transform the points
        self.points = []
        for pt in points:
            x, y, snum = pt
            tform = series.section_tforms[snum][series.alignment]
            x, y = tform.map(x, y, inverted=True)
            self.points.append((x, y, snum))
