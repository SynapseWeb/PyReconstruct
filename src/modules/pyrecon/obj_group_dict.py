class ObjGroupDict():

    def __init__(self, groups : dict = None):
        """Create a two-way dctionary.
        
        Params:
            groups (dict): an existing group dictionary to build from
        """
        self.groups = {}
        self.objects = {}
        if groups:
            for group, obj_list in groups.items():
                for obj in obj_list:
                    self.add(group, obj)

    def add(self, group, obj):
        """Add items to the two-way dictionary."""
        if group not in self.groups:
            self.groups[group] = set()
        self.groups[group].add(obj)
        if obj not in self.objects:
            self.objects[obj] = set()
        self.objects[obj].add(group)
    
    def getObjectGroups(self, obj = None):
        """Get the groups for a given object."""
        return self.objects[obj]
    
    def getGroupObjects(self, group):
        """Get the objects for a given group."""
        return self.groups[group]
    
    def getGroupDict(self):
        """Get a JSON serializable dictionary."""
        groups = self.groups.copy()
        for g in groups:
            groups[g] = list(groups[g])
        return groups
    
    def getGroupList(self):
        """Get a list of groups."""
        return list(self.groups.keys())
    
    def getObjectList(self):
        """Get a list of objects."""
        return list(self.objects.keys())
    