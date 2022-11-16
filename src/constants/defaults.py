from modules.pyrecon.trace import Trace

def getDefaultPaletteTraces():
    """Function to store data for default trace palette"""
    palette_traces = [None] * 20
    n = 0

    new_trace = Trace("circle1", (255, 128, 64))
    new_trace.points = [(-0.5, 0.1667), (-0.5, -0.1667), (-0.1667, -0.5), (0.1667, -0.5), (0.5, -0.1667), (0.5, 0.1667), (0.1667, 0.5), (-0.1667, 0.5)]
    new_trace.resize(0.1)
    palette_traces[n] = new_trace.getDict()
    palette_traces[10+n] = new_trace.getDict()
    n += 1

    new_trace = Trace("star", (128, 0, 255))
    new_trace.points = [(-0.2, 0.1), (-0.5, 0.0), (-0.2, -0.1), (-0.4, -0.4), (-0.1, -0.2), (0.0, -0.5), (0.1, -0.2), (0.4, -0.4), (0.2, -0.1), (0.5, 0.0), (0.2, 0.1), (0.4, 0.4), (0.1, 0.2), (0.0, 0.5), (-0.1, 0.2), (-0.4, 0.4)]
    new_trace.resize(0.1)
    palette_traces[n] = new_trace.getDict()
    palette_traces[10+n] = new_trace.getDict()
    n += 1

    new_trace = Trace("triangle", (255, 0, 128))
    new_trace.points = [(-0.5, -0.5), (0.5, -0.5), (0.0, 0.4167)]
    new_trace.resize(0.1)
    palette_traces[n] = new_trace.getDict()
    palette_traces[10+n] = new_trace.getDict()
    n += 1

    new_trace = Trace("cross", (255, 0, 0))
    new_trace.points = [(-0.5, 0.5), (-0.1429, 0.0), (-0.5, -0.5), (-0.2857, -0.5), (0.0, -0.0714), (0.2857, -0.5), (0.5, -0.5), (0.1429, 0.0), (0.5, 0.5), (0.2857, 0.5), (0.0, 0.0714), (-0.2857, 0.5)]
    new_trace.resize(0.1)
    palette_traces[n] = new_trace.getDict()
    palette_traces[10+n] = new_trace.getDict()
    n += 1

    new_trace = Trace("square", (255, 255, 0))
    new_trace.points = [(0.4, 0.4), (0.4, -0.4), (-0.4, -0.4), (-0.4, 0.3), (-0.5, 0.4), (-0.5, -0.5), (0.5, -0.5), (0.5, 0.5), (-0.5, 0.5), (-0.4, 0.4)]
    new_trace.resize(0.1)
    palette_traces[n] = new_trace.getDict()
    palette_traces[10+n] = new_trace.getDict()
    n += 1

    new_trace = Trace("diamond", (0, 0, 255))
    new_trace.points = [(0.0, 0.5), (-0.5, 0.0), (0.0, -0.5), (0.5, 0.0)]
    new_trace.resize(0.1)
    palette_traces[n] = new_trace.getDict()
    palette_traces[10+n] = new_trace.getDict()
    n += 1

    new_trace = Trace("circle2", (255, 0, 255))
    new_trace.points = [(-0.5, 0.1667), (-0.5, -0.1667), (-0.1667, -0.5), (0.1667, -0.5), (0.5, -0.1667), (0.5, 0.1667), (0.1667, 0.5), (-0.1667, 0.5)]
    new_trace.resize(0.1)
    palette_traces[n] = new_trace.getDict()
    palette_traces[10+n] = new_trace.getDict()
    n += 1

    new_trace = Trace("arrow1", (255, 0, 0))
    new_trace.points = [(0.25, -0.25), (0.0, -0.25), (0.0, -0.125), (0.125, 0.0), (0.5, 0.125), (0.25, 0.25), (0.125, 0.5), (-0.125, 0.25), (-0.25, 0.0), (-0.25, -0.25), (-0.5, -0.25), (-0.125, -0.5)]
    new_trace.resize(0.1)
    palette_traces[n] = new_trace.getDict()
    palette_traces[10+n] = new_trace.getDict()
    n += 1

    new_trace = Trace("plus", (0, 255, 0))
    new_trace.points = [(-0.5, 0.1667), (-0.5, -0.1667), (-0.1667, -0.1667), (-0.1667, -0.5), (0.1667, -0.5), (0.1667, -0.1667), (0.5, -0.1667), (0.5, 0.1667), (0.1667, 0.1667), (0.1667, 0.5), (-0.1667, 0.5), (-0.1667, 0.1667)]
    new_trace.resize(0.1)
    palette_traces[n] = new_trace.getDict()
    palette_traces[10+n] = new_trace.getDict()
    n += 1

    new_trace = Trace("arrow2", (0, 255, 255))
    new_trace.points = [(0.0, 0.5), (0.1667, 0.3333), (-0.5, -0.3333), (-0.3333, -0.5), (0.3333, 0.1667), (0.5, 0.0), (0.5, 0.5)]
    new_trace.resize(0.1)
    palette_traces[n] = new_trace.getDict()
    palette_traces[10+n] = new_trace.getDict()
    n += 1

    return palette_traces
