import numpy as np

import pyqtgraph.opengl as gl

from pyvista.core.pointset import PolyData, UnstructuredGrid

from modules.pyrecon.series import Series

from modules.calc.quantification import centroid

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

    extremes = [None]*6  # xmin xmax ymin, ymax, zmin, zmax

    obj_data = {}
    for obj_name in obj_names:
        obj_data[obj_name] = {}
        if obj_name in series.object_3D_modes:
            obj_data[obj_name]["mode"] = series.object_3D_modes[obj_name]
        else:
            obj_data[obj_name]["mode"] = "surface"
        
        if obj_data[obj_name]["mode"] == "surface":
            obj_data[obj_name]["points"] = []
            obj_data[obj_name]["color"] = None
        elif obj_data[obj_name]["mode"] == "spheres":
            obj_data[obj_name]["points"] = []
            obj_data[obj_name]["radii"] = []
            obj_data[obj_name]["colors"] = []

    # iterate through all sections and gather points (and colors)
    z = 0
    for snum in sorted(series.sections.keys()):
        section = series.loadSection(snum)
        tform = section.tforms[series.alignment]
        for obj_name in obj_names:
            if obj_name in section.contours:
                for trace in section.contours[obj_name]:

                    # collect all points if generating a full surface
                    if obj_data[obj_name]["mode"] == "surface":
                        if not obj_data[obj_name]["color"]:  # get the first trace color
                            color = tuple([c/255 for c in trace.color])
                            obj_data[obj_name]["color"] = color
                        for pt in trace.points:
                            x, y = tform.map(*pt)
                            obj_data[obj_name]["points"].append((x, y, z))
                            extremes = addToExtremes(extremes, x, y, z)
                    
                    # collect only centroids if generating spheres
                    elif obj_data[obj_name]["mode"] == "spheres":
                        # get the point
                        cent = centroid(trace.points)
                        x, y = tform.map(*cent)
                        obj_data[obj_name]["points"].append((x, y, z))
                        extremes = addToExtremes(extremes, x, y, z)
                        # get the radius
                        obj_data[obj_name]["radii"].append(trace.getRadius(tform))
                        # get the color
                        color = tuple([c/255 for c in trace.color])
                        obj_data[obj_name]["colors"].append(color)
        
        z += section.thickness

    # iterate through all objects and create 3D meshes
    items = []
    for obj_name, data in obj_data.items():

        # if generating surface
        if data["mode"] == "surface":
            points = data["points"]
            if not points:
                continue
            color = data["color"]

            # use pyvista to generate the faces
            pdata = PolyData(np.array(points))
            new_pdata = pdata.delaunay_3d(alpha=0.1).extract_surface().smooth_taubin()
            
            # extract face data
            verts = new_pdata.points
            faces = new_pdata.faces.reshape((int(new_pdata.faces.shape[0]/4), 4))
            faces = faces[:, 1:]

            # create object
            sc_item = gl.GLMeshItem(
                    vertexes=verts,
                    faces=faces,
                    color=(*color, alpha),
                    shader="edgeDarken",
                    glOptions="translucent",
                    smooth=True
            )

            items.append(sc_item)
        
        # if generating spheres
        elif data["mode"] == "spheres":
            for point, radius, color in zip(
                data["points"],
                data["radii"],
                data["colors"]
            ):
                sphere = gl.MeshData.sphere(rows=6, cols=6, radius=radius)
                item = gl.GLMeshItem(
                    meshdata=sphere,
                    smooth=True,
                    color=(*color, alpha),
                    shader="edgeDarken",
                    glOptions="translucent",
                )
                item.translate(*point)
                items.append(item)

    return (
        items,
        tuple(extremes)
    )

def addToExtremes(extremes, x, y, z):
    """Keep track of the extreme values."""
    extremes = extremes.copy()
    if extremes[0] is None:
        extremes = [x, x, y, y, z, z]
    else:
        if x < extremes[0]: extremes[0] = x
        if x > extremes[1]: extremes[1] = x
        if y < extremes[2]: extremes[2] = y
        if y > extremes[3]: extremes[3] = y
        if z < extremes[4]: extremes[4] = z
        if z > extremes[5]: extremes[5] = z
    
    return extremes