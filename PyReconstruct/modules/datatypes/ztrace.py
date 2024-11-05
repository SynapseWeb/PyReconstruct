from PyReconstruct.modules.calc import distance3D, rolling_average

from PyReconstruct.modules.datatypes_legacy import ZContour as XMLZContour

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
        if len(self.points) != len(other.points):
            return False
        
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
            tform = series.data["sections"][snum]["tforms"][series.alignment]
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
                tform = section.tform
            else:
                tform = series.data["sections"][pt[2]]["tforms"][series.alignment]
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
                    reversed = False
                else:
                    p2, p1 = prev_pt, pt
                    reversed = True
                if p1[2] <= section.n <= p2[2]:
                    segments = p2[2] - p1[2] + 1
                    x_inc = (p2[0] - p1[0]) / segments
                    y_inc = (p2[1] - p1[1]) / segments
                    segment_i = section.n - p1[2]
                    l = (
                        (
                            p1[0] + segment_i*x_inc,
                            p1[1] + segment_i*y_inc
                        ),
                        (
                            p1[0] + (segment_i+1)*x_inc,
                            p1[1] + (segment_i+1)*y_inc
                        )
                    )
                    if reversed:
                        l = l[::-1]
                    lines.append(l)
        
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

        alignment = series.getAttr(self.name, "alignment", ztrace=True)
        if not alignment: alignment = series.alignment

        real_pts = []
        for x, y, snum in self.points:
            tform = series.data["sections"][snum]["tforms"][alignment]
            new_pt = (*tform.map(x, y), zvals[snum])
            real_pts.append(new_pt)
        
        dist = 0
        for i in range(len(real_pts[:-1])):
            x1, y1, z1 = real_pts[i]
            x2, y2, z2 = real_pts[i+1]
            dist += distance3D(x1, y1, z1, x2, y2, z2)

        return dist

    def getStart(self):
        """Get the first section of the ztrace."""
        return min([s for x, y, s in self.points])

    def getEnd(self):
        """Get the last section of the ztrace."""
        return max([s for x, y, s in self.points])   

    def smooth(self, series, smooth=10):
        """Smooth z-trace via padded moving average.
        
            Params:
                series (Series): the series object (contains transform data)
                smooth (int): the smoothing factor
        """
        ## Transform points
        points = []

        z_align = series.getAttr(self.name, "alignment", ztrace=True)
        snums = []

        for pt in self.points:
            
            x, y, snum = pt

            tform = series.data["sections"][snum]["tforms"][z_align]
            x, y = tform.map(x, y)

            snums.append(snum)
            points.append((x, y))

        ## Calculate rolling average
        points = rolling_average(points, smooth, edge_mode="padded")
        
        ## De-transform points to base image coordinates
        self.points = []
        points = [p + (s,) for p, s in zip(points, snums)]  # re-combine snums with points

        for pt in points:
            x, y, snum = pt
            tform = series.data["sections"][snum]["tforms"][z_align]
            x, y = tform.map(x, y, inverted=True)
            self.points.append((x, y, snum))
    
    def magScale(self, section_num : int, prev_mag : float, new_mag : float):
        """Adjust the ztrace points to a new magnification.
        
            Params:
                section_number (int): the section number whose magnification is being changed
                prev_mag (float): the previous magnification
                new_mag (float): the new magnification being set
        """
        for i, (x, y, snum) in enumerate(self.points):
            if snum == section_num:
                x *= new_mag / prev_mag
                y *= new_mag / prev_mag
                self.points[i] = (x, y, snum)
