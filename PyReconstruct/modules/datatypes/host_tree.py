import os
import re

class HostTree():

    def __init__(self, host_dict : dict, series):
        """Create the HostTree from a dictionary of (obj_name, hosts)
        
            Params:
                host_dict (dict): the dictionary of (obj_name, hosts)
                series (Series): the series that contains the host tree
        """
        self.objects = {}

        for obj_name, hosts in host_dict.items():
            self.add(obj_name, hosts)

        self.series = series
    
    def add(self, obj_name : str, hosts : list):
        """Add an entry to the host tree.
        
            Params:
                obj_name (str): the name of the object
                hosts (list): the hosts of the above obj
        """

        if isinstance(hosts, str):
            hosts = [hosts]
        
        for name in ([obj_name] + list(hosts)):
            if name not in self.objects:
                self.objects[name] = {
                    "hosts": set(),
                    "travelers": set(),
                }
        
        for host in hosts:
            self.objects[obj_name]["hosts"].add(host)
            self.objects[host]["travelers"].add(obj_name)
        
        # special case: if one of the hosts if hosted by another of the hosts, trim to lowest-level host
        self.checkRedundantHosts()
    
    def checkRedundantHosts(self):
        """Check if any objects are hosted by multiple objects that are already hosts of each other."""
        for obj_name in self.objects:
            superhosts = self.getHosts(obj_name, True, True)
            for superhost in superhosts:
                if superhost in self.getHosts(obj_name):
                    self.objects[obj_name]["hosts"].remove(superhost)
                    self.objects[superhost]["travelers"].remove(obj_name)
    
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
            s = set() if only_secondary else set(hosts.copy())
            for h in hosts:
                s = s.union(set(self.getHosts(h, traverse)))
            return list(s)
    
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
            s = set() if only_secondary else set(travelers.copy())
            for t in travelers:
                s = s.union(set(self.getTravelers(t, traverse)))
            return list(s)
    
    def getObjToUpdate(self, obj_names : list):
        """Get object names that require table updating in the GUI if the given obj(s) are modified."""
        modified_objs = set(obj_names)
        for name in obj_names:
            modified_objs = modified_objs.union(
                self.getTravelers(name, True)
            )
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
        return HostTree(self.getDict(), self.series)

    def getHostGroup(self, obj_name : str, obj_pool=None):
        """Get the full list of obj names in a host group with the given obj.
        
            Params:
                obj_name (str): an object in the host group.
        """
        host_group = [obj_name]
        stack = [obj_name]
        while stack:
            n = stack.pop()
            travelers = self.getTravelers(n)
            hosts = self.getHosts(n)
            for n in (travelers + hosts):
                if n not in host_group and (not obj_pool or n in obj_pool):
                    host_group.append(n)
                    stack.append(n)
        return host_group
    
    def merge(self, other, regex_filters=None, restrict_to=[]):
        """Merge two host trees together.
        
            Params:
                other (HostTree): the other host tree
                regex_filters (list): the list of regex filters required to pass
        """
        for obj_name, d in other.objects.items():

            if restrict_to and obj_name not in restrict_to:
                    continue

            
            if (
                    obj_name not in self.series.data["objects"] or
                    not passesFilters(obj_name, regex_filters)
            ):
                continue

            hosts = d["hosts"]
            hosts = [h for h in d["hosts"] if passesFilters(h, regex_filters)]
            self.add(obj_name, hosts)
    
    def getASCII(self, obj_name : str, hosts=True, prefix=""):
        """Get an ASCII representation of the hosts/travelers of an object.
        
            Params:
                obj_name (str): the name of the object
                hosts (bool): True if host tree, False if traveler tree
                prefix (str): used in recursion
        """
        if prefix == "":
            tree_str = obj_name + "\n"
            if obj_name not in self.objects:
                return tree_str
        else:
            tree_str = ""
        
        objs = sorted(list(self.objects[obj_name][("hosts" if hosts else "travelers")]))
        for i, obj in enumerate(objs):
            # determine if extra statement should be added
            extras = sorted(list(self.objects[obj][("travelers" if hosts else "hosts")]))
            extras.remove(obj_name)
            if extras:
                s = "also hosts:" if hosts else "also hosted by:"
                extra_str = f" ({s} {', '.join(extras[:3])}{('' if len(extras) <= 3 else '...')})"
            else:
                extra_str = ""
            
            if i == len(objs) - 1:
                tree_str += prefix + "└── " + obj + extra_str + "\n"
                new_prefix = prefix + "    "
            else:
                tree_str += prefix + "├── " + obj + extra_str + "\n"
                new_prefix = prefix + "│   "
            if obj in self.objects:
                tree_str += self.getASCII(obj, hosts, new_prefix)
        
        return tree_str


def passesFilters(s, re_filters):
    if not re_filters:
        return True
    for rf in re_filters:
        if bool(re.fullmatch(rf, s)):
            return True
    return False


def generate_directory_tree_string(path, prefix=""):
    tree_string = ""
    
    # Check if the path is a directory
    if os.path.isdir(path):
        # Get list of files and directories
        items = os.listdir(path)
        items.sort()
        for i, item in enumerate(items):
            item_path = os.path.join(path, item)
            # Determine the correct prefix for each item
            if i == len(items) - 1:
                tree_string += prefix + "└── " + item + "\n"
                new_prefix = prefix + "    "
            else:
                tree_string += prefix + "├── " + item + "\n"
                new_prefix = prefix + "│   "
            # Recurse if the item is a directory
            if os.path.isdir(item_path):
                tree_string += generate_directory_tree_string(item_path, new_prefix)
    else:
        tree_string = f"{path} is not a directory\n"
    
    return tree_string
