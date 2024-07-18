from typing import Union

from .objects_3D import Surface, Spheres, Contours, Ztrace3D

from PyReconstruct.modules.datatypes import Series


Series_like_obj = Union[Series, str]  # can be type statement in >=3.12


def generateVolumes(series_like : Series_like_obj, objs : dict, ztraces : dict):
    """Generate the volume items for a set of objects.
    
        Params:
            series_like (Series or str): The series of fp to a series containing object data
            objs (dict): a dict of objects to construct (dict containing name, color, alpha, tform)
            ztrace_names (list): the list of ztraces to construct (dict containing name, color, alpha, tform)
            alpha (float): the transparency for the 3D scene
        Returns:
            (list): the 3D item objects
            (tuple): xmin, xmax, ymin, ymax, zmin, zmax
    """
    # option to use fp instead of series
    if isinstance(series_like, str):
        series = Series.openJser(series_like)
    else:
        series = series_like

    # check the obj names
    for d in objs.copy():
        if d["name"] not in series.data["objects"]:
            objs.remove(d)
    # check the ztrace names
    for d in ztraces.copy():
        if d["name"] not in series.ztraces:
            ztraces.remove(d)
    
    # create the 3D objects
    obj_data = {}
    for d in objs:
        name = d["name"]
        mode = series.getAttr(name, "3D_mode")
        color = d["color"] if "color" in d else None
        alpha = d["alpha"] if "alpha" in d else None
        tform = d["tform"] if "tform" in d else None
        args = (name, series, color, alpha, tform)
        if mode == "surface":
            obj_data[name] = Surface(*args)
        elif mode == "spheres":
            obj_data[name] = Spheres(*args)
        elif mode == "contours":
            obj_data[name] = Contours(*args)

    # iterate through all sections and gather points (and colors)
    mags = []
    thicknesses = []

    for snum, section in series.enumerateSections(show_progress=False):
        # ASSUME SOMEWHAT UNIFORM THICKNESS
        thicknesses.append(section.thickness)
        mags.append(section.mag)

        for obj_name in obj_data.keys():
            if obj_name in section.contours:
                # get the transform sepcific to the object
                alignment = series.getAttr(obj_name, "alignment")
                if not alignment:
                    tform = section.tform
                else:
                    tform = section.tforms[alignment]
                for trace in section.contours[obj_name]:
                    # collect all points if generating a full surface
                    obj_data[obj_name].addTrace(trace, snum, tform)
    
    # create ztraces
    ztrace_data = {}
    for d in ztraces:
        name = d["name"]
        color = d["color"] if "color" in d else None
        alpha = d["alpha"] if "alpha" in d else None
        tform = d["tform"] if "tform" in d else None
        args = (name, series, color, alpha, tform)
        ztrace_data[name] = Ztrace3D(*args)


    # iterate through all objects and create 3D meshes
    mesh_data_list = []
    extremes = []

    for obj_name, obj_3D in obj_data.items():
        extremes = addToExtremes(extremes, obj_3D.extremes)

        if type(obj_3D) is Surface:
            mesh_data_list.append(obj_3D.generate3D())
        elif type(obj_3D) is Spheres:
            mesh_data_list.append(obj_3D.generate3D())
        elif type(obj_3D) is Contours:
            mesh_data_list.append(obj_3D.generate3D())
    
    for _, ztrace_3D in ztrace_data.items():
        mesh_data = ztrace_3D.generate3D()
        extremes = addToExtremes(extremes, ztrace_3D.extremes)
        mesh_data_list.append(mesh_data)
    
    # convert snum extremes to z extremes
    t = series.avg_thickness
    extremes[4] *= t
    extremes[5] *= t
    
    # return list tuples (volume, opengl objects)
    # return global bounding box to set view
    return (
        mesh_data_list,
        series
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
