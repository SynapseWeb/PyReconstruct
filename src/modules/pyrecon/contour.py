from modules.pyrecon.trace import Trace

class Contour():

    def __init__(self, name : str, traces : list = []):
        """Create a contour object.
        
            Params:
                name (str): the name of the contour
                traces (list): the existing list of traces
        """
        self.name = name
        for trace in traces:
            if trace.name != name:
                raise Exception("Trace name does not match contour name")
        self.traces = traces
    
    def __iter__(self):
        """Return the iterator object for the traces list"""
        return self.traces.__iter__()
    
    def __getitem__(self, index):
        """Allow the user to index the traces list."""
        return self.traces[index]
    
    def __len__(self):
        """Get the length of the trace list."""
        return len(self.traces)
    
    def __add__(self, other):
        """Combine contours."""
        if self.name != other.name:
            raise Exception("Only contours with the same name can be summed.")
        return Contour(
            self.name,
            self.traces + other.traces
        )
    
    def append(self, trace : Trace):
        """Append a trace to the existing traces."""
        if trace.name != self.name:
            raise Exception("Trace name does not match contour name")
        self.traces.append(trace)
    
    def remove(self, trace : Trace):
        """Remove a trace from the list."""
        self.traces.remove(trace)
    
    def index(self, trace : Trace):
        """Find the index of a trace in the list."""
        return self.traces.index(trace)
    
    def isEmpty(self):
        """Return True if list if empty."""
        return not bool(self.traces)
    
    def getTraces(self):
        """Return the list of traces."""
        return self.traces
    
    def copy(self):
        """Return a copy of the contour."""
        traces = []
        for trace in self.traces:
            traces.append(trace.copy())
        return Contour(self.name, traces)


