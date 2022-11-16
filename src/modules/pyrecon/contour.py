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

