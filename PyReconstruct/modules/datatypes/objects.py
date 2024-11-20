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
        if obj_name in self.getNames():
            return SeriesObject(self.series, obj_name)
        else:
            return None

    def getNames(self):
        """Return all of the object names."""
        return list(sorted(self.series.data["objects"].keys()))

    def exportCSV(self, out_fp : str = None):
        """Export a CSV containing the quantitative data for all objects.
        
            Params:
                out_fp (str): filepath for newly created CSV (function returns str if filepath not provided)
        """
        sep = "|"
        
        out_str = f"Series{sep}Name{sep}Start{sep}End{sep}Count{sep}Flat_Area{sep}Volume{sep}Groups{sep}"
        out_str += f"Trace_Tags{sep}Last_User{sep}Curation_Status{sep}Curation_User{sep}"
        out_str += f"Curation_Date{sep}Alignment{sep}Comment\n"

        series_code = self.series.code

        for obj_name in sorted(self.series.data["objects"].keys()):

            out_str += f"{series_code}{sep}"
            out_str += f"{obj_name}{sep}"
            out_str += f"{self.series.data.getStart(obj_name)}{sep}"
            out_str += f"{self.series.data.getEnd(obj_name)}{sep}"
            out_str += f"{self.series.data.getCount(obj_name)}{sep}"
            out_str += f"{self.series.data.getFlatArea(obj_name)}{sep}"
            out_str += f"{self.series.data.getVolume(obj_name)}{sep}"
            out_str += f"{':'.join(self.series.object_groups.getObjectGroups(obj_name))}{sep}"
            out_str += f"{':'.join(self.series.data.getTags(obj_name))}{sep}"
            out_str += f"{self.series.getAttr(obj_name, 'last_user')}{sep}"
            curation = self.series.getAttr(obj_name, "curation")

            if curation:
                status, user, date = tuple(curation)
                if status:
                    status = "Curated"
                else:
                    status = "Needs Curation"
            else:
                status = user = date = ""

            out_str += f"{status}{sep}{user}{sep}{date}{sep}"

            alignment = self.series.getAttr(obj_name, "alignment")
            if not alignment: alignment = ""
            out_str += f"{alignment}{sep}"

            ## Remove seperator from comments
            comments = self.series.getAttr(obj_name, "comment").replace(sep, "_")
            out_str += comments + "\n"
            
        if out_fp:
            
            with open(out_fp, "w") as f:
                f.write(out_str)

        return out_str

    def getSourceAttrs(self, source_obj) -> tuple:
        """Get relavant source obj attrs."""
        
        series_obj = SeriesObject(self.series, source_obj)

        return (
            series_obj.alignment,                # alignment 
            set(series_obj.groups),              # groups
            self.series.getObjHosts(source_obj)  # hosts
        )

    def assignCopyAttrs(self, target_obj, alignment: str, groups: list, hosts: str) -> None:
        """Assign relevant attributes to copied objects."""

        ## Alignments
        self.series.setAttr(
            target_obj, "alignment", alignment, ztrace=False
        )

        ## Groups
        for group in groups:  # groups
            self.series.object_groups.add(group, target_obj)  # groups

        ## Hosts
        self.series.setObjHosts([target_obj], hosts)

    def copyObjAttrs(self, source_obj: str, target_obj: str) -> None:
        """Copy relavant obj attrs to another obj."""

        alignment, groups, hosts = self.getSourceAttrs(source_obj)
        self.assignCopyAttrs(target_obj, alignment, groups, hosts)        
        
    
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
        return self.series.getAttr(self.name, "3D_mode")
    @mode_3D.setter
    def mode_3D(self, value):
        return self.series.setAttr(self.name, "3D_mode", value)
    @property
    def opacity_3D(self):
        return self.series.getAttr(self.name, "3D_opacity")
    @mode_3D.setter
    def opacity_3D(self, value):
        return self.series.setAttr(self.name, "3D_opacity", value)
    
    
    @property
    def last_user(self):
        return self.series.getAttr(self.name, "last_user")
    @last_user.setter
    def last_user(self, value):
        self.series.getAttr(self.name, "last_user", value)
    
    @property
    def curation(self):
        return self.series.getAttr(self.name, "curation")
    @curation.setter
    def curation(self, value):
        self.series.getAttr(self.name, "curation", value)
    
    @property
    def comment(self):
        return self.series.getAttr(self.name, "comment")
    @comment.setter
    def comment(self, value):
        self.series.getAttr(self.name, "comment", value)
    
    @property
    def alignment(self):
        return self.series.getAttr(self.name, "alignment")
    @alignment.setter
    def alignment(self, value):
        self.series.getAttr(self.name, "alignment", value)
        self.series.data.refresh()  # refresh the series data
    
    @property
    def groups(self):
        return self.series.object_groups.getObjectGroups(self.name)
