class ObjGroupDict():

    def __init__(self, groups : dict = None):
        """Create a two-way dictionary.
        
        Params:
            groups (dict): an existing group dictionary to build from
        """
        self.groups = {}
        self.objects = {}
        if groups:
            for group, obj_list in groups.items():
                for obj in obj_list:
                    self.add(group, obj)

    def add(self, group : str, obj : str):
        """Add items to the two-way dictionary.
        
            Params:
                group (str): the group
                obj (str): the object to add to the group"""
        if group not in self.groups:
            self.groups[group] = set()
        self.groups[group].add(obj)
        if obj not in self.objects:
            self.objects[obj] = set()
        self.objects[obj].add(group)
    
    def remove(self, group : str, obj : str):
        """Remove items from the two-way dictionary.
        
            Params:
                group (str): the group
                obj (str): the object to remove from the group
        """
        if group in self.groups and obj in self.groups[group]:
            self.groups[group].remove(obj)
        else:
            return False
        self.objects[obj].remove(group)

        # check if anything is empty
        if not self.groups[group]:
            del self.groups[group]
        if not self.objects[obj]:
            del self.objects[obj]
        
        return True
    
    def getObjectGroups(self, obj : str = None) -> set:
        """Get the groups for a given object.
        
            Params:
                obj (str): the object to get the groups for
        """
        try:
            return self.objects[obj]
        except KeyError:
            return set()
    
    def getGroupObjects(self, group : str) -> set:
        """Get the objects for a given group.
        
            Params:
                group (str): the group to get objects for
        """
        try:
            return self.groups[group]
        except KeyError:
            return set()

    def getGroupDict(self) -> dict:
        """Get a JSON serializable dictionary."""
        groups = self.groups.copy()
        for g in groups:
            groups[g] = list(groups[g])
        return groups
    
    def getGroupList(self) -> list:
        """Get a list of groups."""
        return list(self.groups.keys())
    
    def getObjectList(self) -> list:
        """Get a list of objects."""
        return list(self.objects.keys())
    
