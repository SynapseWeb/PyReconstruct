"""Export 3D objects."""

import os
from pathlib import Path

from .objects_3D import Surface, Spheres, Contours

from PyReconstruct.modules.datatypes import Series
from PyReconstruct.modules.gui.utils import notify

def export3DObjects(series: Series, obj_names : list, output_dir : str, export_type = str):
    """Export 3D objects.

        Params:
            series (Series): the series containing the object data
            obj_names (list): a list of objects to export
            output_dir (str): directory to place exported files
            export_type (str): export format
        Returns:
            void
    """

    obj_data = {}

    for obj_name in obj_names:

        mode, opacity = tuple(series.getAttr(obj_name, "3D_modes"))

        match mode:
            
            case "surface":
                obj_data[obj_name] = (Surface(obj_name), opacity)
                
            case "spheres":
                obj_data[obj_name] = (Spheres(obj_name), opacity)
                
            case "contours":
                obj_data[obj_name] = (Contours(obj_name), opacity)

    # iterate through all sections and gather points (and colors)
    mags = []
    thicknesses = []

    for snum, section in series.enumerateSections(show_progress=False):

        # Assume somewhat uniform section thickness
        thicknesses.append(section.thickness)
        mags.append(section.mag)
        tform = section.tform

        for obj_name in obj_names:
            
            if obj_name in section.contours:
                
                for trace in section.contours[obj_name]:
                    
                    # collect all points if generating a full surface
                    obj_data[obj_name][0].addTrace(trace, snum, tform)

    # iterate through all objects and export 3D meshes
    
    avg_mag = sum(mags) / len(mags)
    avg_thickness = sum(thicknesses) / len(thicknesses)

    for obj_name, (obj_3D, opacity) in obj_data.items():

        output_dir = Path(output_dir)
        output_file = output_dir / f"{obj_name}.{export_type}"

        match obj_3D:

            case Surface():

                # get the vres from the series options
                vres_min = min(avg_mag, avg_thickness)
                vres_max = max(avg_mag, avg_thickness)
                vres_percent = series.getOption("3D_xy_res")
                vres = vres_min + (vres_percent / 100) * (vres_max - vres_min)

                obj_3D.exportTrimesh(
                    output_file,
                    export_type,
                    vres,
                    avg_thickness,
                    opacity,
                    series.getOption("3D_smoothing"),
                )

            case Spheres():

                obj_3D.exportTrimesh(
                    output_file,
                    export_type,
                    avg_thickness,
                    opacity
                )

            case Contours():

                pass

    notify(f"Object(s) exported to directory:\n\n{output_dir.absolute()}\n")
