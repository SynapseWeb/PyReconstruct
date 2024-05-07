from .trace import Trace
from .flag import Flag

class Contour():

    def __init__(self, name : str, traces : list[Trace] = None):
        """Create a contour object.
        
            Params:
                name (str): the name of the contour
                traces (list): the existing list of traces
        """
        self.name = name
        if traces:
            for trace in traces:
                if trace.name != name:
                    raise Exception(f"Trace name \"{trace.name}\" does not match contour name \"{name}\"")
            self.traces : list[Trace] = traces
        else:
            self.traces : list[Trace] = []
    
    def __iter__(self):
        """Return the iterator object for the traces list"""
        return self.traces.__iter__()
    
    def __getitem__(self, index) -> Trace:
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
        """Append a trace to the existing traces.
        
            Params:
                trace (Trace): the trace to append to the contour
        """
        if trace.name != self.name:
            raise Exception("Trace name does not match contour name")
        self.traces.append(trace)
    
    def remove(self, trace : Trace):
        """Remove a trace from the list.
        
            Params:
                trace (Trace): the trace to remove from the contour
        """
        self.traces.remove(trace)
    
    def index(self, trace : Trace):
        """Find the index of a trace in the list.
        
            Params:
                trace (Trace): the trace to find the index for
        """
        return self.traces.index(trace)
    
    def isEmpty(self) -> bool:
        """Return True if no traces associated with contour."""
        return not bool(self.traces)
    
    def getTraces(self) -> list:
        """Return the list of traces."""
        return self.traces.copy()
    
    def copy(self):
        """Return a copy of the contour."""
        traces = []
        for trace in self.traces:
            traces.append(trace.copy())
        return Contour(self.name, traces)
    
    def getBounds(self, tform=None):
        """Get the bounds of the contour.

            Params:
                tform (Transform): the transform to apply to the traces
            Returns:
                (tuple): the (xmin, ymin, xmax, ymax) extremes for the contours"""
        values = [[], [], [], []]
        for trace in self.traces:
            for i, v in enumerate(trace.getBounds(tform)):
                values[i].append(v)
        
        xmin = min(values[0])
        ymin = min(values[1])
        xmax = max(values[2])
        ymax = max(values[3])

        return xmin, ymin, xmax, ymax

    def getMidpoint(self, tform=None):
        """Get the midpoint of the contour (average of extremes).
        
            Params:
                tform (Transform): the transform to apply to the traces
            Returns:
                (tuple): the x, y coords for the midpoint
        """
        xmin, ymin, xmax, ymax = self.getBounds(tform)

        return (xmax + xmin) / 2, (ymax + ymin) / 2

    def importTraces(self, other, threshold : float = 0.95, keep_above : str = "self"):
        """Import all of the traces from another contour.
        
            Params:
                other (Contour): the contour with traces to import
                threshold (float): the overlap threshold
                keep_above (str): the series that is favored for functional duplicates (above the overlap threshold; "self", "other", or "")
        """
        # keep track of new trace list
        traces = []
        # repeated use: determining which traces to use when finding duplicates
        def addDuplicate(st : Trace, ot : Trace, tlist : list):
            if keep_above == "self":
                st.mergeTags(ot)  # import tags
                tlist.append(st)
            elif keep_above == "other":
                ot.mergeTags(st)
                tlist.append(ot)
            elif keep_above == "":
                tlist += [st, ot]
            else:
                raise Exception(f"Invalid key {keep_above} used for keep_above parameter.")

        # assume that the first few traces are the same to save time
        i = 0
        while i < len(other):
            if i >= len(self):
                break
            s_trace = self[i]
            o_trace = other[i]
            if s_trace.overlaps(o_trace, threshold):
                addDuplicate(s_trace, o_trace, traces)
            else:
                break
            i += 1

        # gather remaining traces that aren't the same between series
        rem_s_traces = self[i:]
        rem_o_traces = other[i:]
        first_comparison = True
        for o_trace in rem_o_traces.copy():
            found_i = None
            for i, s_trace in enumerate(rem_s_traces):
                if first_comparison:  # skip the first comparison -- we already know its false
                    first_comparison = False
                    continue
                if s_trace.overlaps(o_trace, threshold=0.95):
                    addDuplicate(s_trace, o_trace, traces)
                    found_i = i
                    break
            if found_i is not None:
                rem_s_traces.pop(found_i)
                rem_o_traces.remove(o_trace)
        traces += rem_s_traces + rem_o_traces
        
        # replace traces list with new list
        self.traces = traces
        
        # return the possible conflict traces
        return rem_s_traces, rem_o_traces

        
