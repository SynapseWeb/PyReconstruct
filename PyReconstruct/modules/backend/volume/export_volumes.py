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

        mode = series.getAttr(obj_name, "3D_mode")

        match mode:
            
            case "surface":
                obj_data[obj_name] = Surface(obj_name, series)
                
            case "spheres":
                obj_data[obj_name] = Spheres(obj_name, series)
                
            case "contours":
                obj_data[obj_name] = Contours(obj_name, series)

    for snum, section in series.enumerateSections(show_progress=False):

        # Assume somewhat uniform section thickness
        tform = section.tform

        for obj_name in obj_names:
            
            if obj_name in section.contours:
                
                for trace in section.contours[obj_name]:
                    
                    # collect all points if generating a full surface
                    obj_data[obj_name][0].addTrace(trace, snum, tform)

    # iterate through all objects and export 3D meshes

    for obj_name, obj_3D in obj_data.items():

        output_dir = Path(output_dir)
        output_file = output_dir / f"{obj_name}.{export_type}"

        match obj_3D:

            case Surface():

                obj_3D.exportTrimesh(
                    output_file,
                    export_type,
                )

            case Spheres():

                obj_3D.exportTrimesh(
                    output_file,
                    export_type,
                )

            case Contours():

                pass

    notify(f"Object(s) exported to directory:\n\n{output_dir.absolute()}\n")
