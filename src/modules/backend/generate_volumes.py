from modules.backend.objects_3D import Surface, Spheres

from modules.pyrecon.series import Series

def generateVolumes(series : Series, obj_names : list, alpha : float):
    """Generate the volume items for a set of objects.
    
        Params:
            series (Series): the series containing the object data
            obj_names (list): the list of objects to reconstruct
            alpha (float): the transparency for the 3D scene
        Returns:
            (list): the 3D item objects
            (tuple): xmin, xmax, ymin, ymax, zmin, zmax
    """
    # load the data from the series

    # create the 3D objects
    obj_data = {}
    for obj_name in obj_names:
        if obj_name in series.object_3D_modes:
            mode = series.object_3D_modes[obj_name]
            if mode == "surface":
                obj_data[obj_name] = Surface(obj_name)
            elif mode == "spheres":
                obj_data[obj_name] = Spheres(obj_name)
        else:
            obj_data[obj_name] = Surface(obj_name)

    # iterate through all sections and gather points (and colors)
    z = 0
    mags = []
    for snum in sorted(series.sections.keys()):
        section = series.loadSection(snum)

        mags.append(section.mag)
        tform = section.tforms[series.alignment]

        for obj_name in obj_names:
            if obj_name in section.contours:
                for trace in section.contours[obj_name]:
                    # collect all points if generating a full surface
                    obj_data[obj_name].addTrace(trace, z, tform)
        
        z += section.thickness

    # iterate through all objects and create 3D meshes
    items = []
    extremes = []

    for obj_name, obj_3D in obj_data.items():
        extremes = addToExtremes(extremes, obj_3D.extremes)

        if type(obj_3D) is Surface:
            items.append(obj_3D.generate3D(alpha))
        elif type(obj_3D) is Spheres:
            items += (obj_3D.generate3D(alpha))

    return (
        items,
        tuple(extremes)
    )

def addToExtremes(extremes, new_extremes):
    """Keep track of the extreme values."""
    e = extremes.copy()
    if not e:
        e = new_extremes
    else:
        ne = new_extremes
        if ne[0] < e[0]: e[0] = ne[0]
        if ne[1] > e[1]: e[1] = ne[1]
        if ne[2] < e[2]: e[2] = ne[2]
        if ne[3] > e[3]: e[3] = ne[3]
        if ne[4] < e[4]: e[4] = ne[4]
        if ne[5] > e[5]: e[5] = ne[5]

    return e