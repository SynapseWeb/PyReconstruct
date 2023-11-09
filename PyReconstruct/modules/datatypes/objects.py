class Objects():

    def __init__(self, series):
        """Create the objects attribute for the series.
        
            Params:
                series (Series): the series containing the objects"""
        self.series = series
    
    def __getitem__(self, obj_name : str):
        """Index the objects.
        
            Params:
                obj_name (str): the name of the object
        """
        return SeriesObject(self.series, obj_name)

class SeriesObject():

    def __init__(self, series, obj_name : str):
        """Create the object to access the series.
        
            Params:
                series (Series): the series containing the object
                name (str): the name of the object
        """
        self.series = series
        self.obj_name = obj_name
    
    @property
    def name(self):
        return self.obj_name
    @name.setter
    def name(self, value):
        self.series.editObjectAttributes([self.obj_name], name=value)
        self.obj_name = value
       
    @property
    def start(self):
        return self.series.data.getStart(self.name)
    @property
    def end(self):
        return self.series.data.getEnd(self.name)
    @property
    def count(self):
        return self.series.data.getCount(self.name)
    @property
    def flat_area(self):
        return self.series.data.getFlatArea(self.name)
    @property
    def volume(self):
        return self.series.data.getVolume(self.name)

    @property
    def mode_3D(self):
        return self.series.getObjAttr(self.name, "3D_modes")
    @mode_3D.setter
    def mode_3D(self, value):
        return self.series.setObjAttr(self.name, "3D_modes", value)
    
    @property
    def last_user(self):
        return self.series.getObjAttr(self.name, "last_user")
    @last_user.setter
    def last_user(self, value):
        self.series.getObjAttr(self.name, "last_user", value)
    
    @property
    def curation(self):
        return self.series.getObjAttr(self.name, "curation")
    @curation.setter
    def curation(self, value):
        self.series.getObjAttr(self.name, "curation", value)
    
    @property
    def comment(self):
        return self.series.getObjAttr(self.name, "comment")
    @comment.setter
    def comment(self, value):
        self.series.getObjAttr(self.name, "comment", value)
    
    @property
    def alignment(self):
        return self.series.getObjAttr(self.name, "alignment")
    @alignment.setter
    def alignment(self, value):
        self.series.getObjAttr(self.name, "alignment", value)