class HostTree():

    def __init__(self, host_dict : dict):
        """Create the HostTree from a dictionary of (obj_name, hosts)
        
            Params:
                host_dict (dict): the dictionary of (obj_name, hosts)
        """
        self.objects = {}
        for obj_name, hosts in host_dict.items():
            self.add(obj_name, hosts)
    
    def add(self, obj_name : str, hosts : list):
        """Add an entry to the host tree.
        
            Params:
                obj_name (str): the name of the object
                hosts (list): the hosts of the above obj
        """
        for name in ([obj_name] + list(hosts)):
            if name not in self.objects:
                self.objects[name] = {
                    "hosts": set(),
                    "travelers": set(),
                }
        
        for host in hosts:
            self.objects[obj_name]["hosts"].add(host)
            self.objects[host]["travelers"].add(obj_name)
    
    def removeObject(self, obj_name : str):
        """Remove an object from the tree."""
        if obj_name not in self.objects:
            return
        
        hosts = self.getHosts(obj_name)
        for host in hosts:
            self.objects[host]["travelers"].remove(obj_name)
        travelers = self.getTravelers(obj_name)
        for traveler in travelers:
            self.objects[traveler]["hosts"].remove(obj_name)
        del(self.objects[obj_name])
    
    def renameObject(self, old_name : str, new_name : str):
        """Rename an object in the tree."""
        hosts = self.getHosts(old_name)
        travelers = self.getTravelers(old_name)
        self.removeObject(old_name)
        self.add(new_name, hosts)
        for traveler in travelers:
            self.add(traveler, [new_name])
    
    def clearHosts(self, obj_name : str):
        """Clear ONLY THE HOSTS for a specific object."""
        # check for existence of object
        if obj_name not in self.objects:
            return
        
        hosts = self.getHosts(obj_name)
        for host in hosts:
            self.objects[host]["travelers"].remove(obj_name)
        self.objects[obj_name]["hosts"] = set()
    
    def getHosts(self, obj_name : str, traverse=False, only_secondary=False):
        """Get the hosts of a certain object.
        
            Params:
                obj_name (str): the object to get the hosts of
                traverse (bool): True if returning the hosts of hosts and so on
        """
        if obj_name not in self.objects:
            return []
        
        hosts = list(self.objects[obj_name]["hosts"]).copy()
        if not traverse:
            return hosts
        else:
            l = [] if only_secondary else hosts.copy()
            for h in hosts:
                l += self.getHosts(h, traverse)
            return l
    
    def getTravelers(self, obj_name : str, traverse=False, only_secondary=False):
        """Get the objects that are hosted by the requested object
        
            Params:
                obj_name (str): the host of the returned objects
                traverse (bool): True if returning the travelers of travelers and so on
        """
        if obj_name not in self.objects:
            return []
        
        travelers = list(self.objects[obj_name]["travelers"]).copy()
        if not traverse:
            return travelers
        else:
            l = [] if only_secondary else travelers.copy()
            for t in travelers:
                l += self.getTravelers(t, traverse)
            return l
    
    def getObjToUpdate(self, obj_names : list):
        """Get object names that require table updating in the GUI if the given obj(s) are modified."""
        modified_objs = set(obj_names)
        for name in obj_names:
            modified_objs = modified_objs.union(
                self.getTravelers(name, True)
            )
        print(modified_objs)
        return modified_objs
    
    def getDict(self):
        """Return the tree in dict format."""
        d = {}
        for obj_name, hosts_travelers in self.objects.items():
            hosts = hosts_travelers["hosts"]
            if not hosts:
                continue
            d[obj_name] = list(hosts.copy())
        return d

    def copy(self):
        return HostTree(self.getDict())
