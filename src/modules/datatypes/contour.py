from .trace import Trace

class Contour():

    def __init__(self, name : str, traces : list = None):
        """Create a contour object.
        
            Params:
                name (str): the name of the contour
                traces (list): the existing list of traces
        """
        self.name = name
        if traces:
            for trace in traces:
                if trace.name != name:
                    raise Exception("Trace name does not match contour name")
            self.traces = traces
        else:
            self.traces = []
    
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
        """Return True if no traces associated with contour."""
        return not bool(self.traces)
    
    def getTraces(self):
        """Return the list of traces."""
        return self.traces.copy()
    
    def copy(self):
        """Return a copy of the contour."""
        traces = []
        for trace in self.traces:
            traces.append(trace.copy())
        return Contour(self.name, traces)
    
    def getMidpoint(self):
        """Get the midpoint of the contour (average of extremes)."""
        values = [[], [], [], []]
        for trace in self.traces:
            for i, v in enumerate(trace.getBounds()):
                values[i].append(v)
        
        xmin = min(values[0])
        ymin = min(values[1])
        xmax = max(values[2])
        ymax = max(values[3])

        return (xmax + xmin) / 2, (ymax + ymin) / 2

    def importTraces(self, other):
        """Import all of the traces from another contour.
        
            Params:
                other (Contour): the contour with traces to import
        """
        # assume that the first few traces are the same to save time
        for i, o_trace in enumerate(other):
            if i >= len(self):
                break
            s_trace = self[i]
            if not s_trace.overlaps(o_trace):
                break
        
        # gather remaining traces and compare them
        rem_s_traces = self[i:]
        rem_o_traces = other[i:]
        for o_trace in rem_o_traces:
            found = False
            found_i = None
            for i, s_trace in enumerate(rem_s_traces):
                if s_trace.overlaps(o_trace):
                    found = True
                    found_i = i
                    break
            if found:
                rem_s_traces.pop(found_i)
            else:
                self.append(o_trace.copy())