"""Export 3D objects."""

import os
from pathlib import Path

from cv2 import transform

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
            
        if mode == "surface":
            obj_data[obj_name] = Surface(obj_name, series)
            
        elif mode == "spheres":
            obj_data[obj_name] = Spheres(obj_name, series)
            
        elif mode == "contours":
            obj_data[obj_name] = Contours(obj_name, series)

    for snum, section in series.enumerateSections(show_progress=False):

        # # Assume somewhat uniform section thickness
        # tform = section.tform

        for obj_name in obj_names:

            if obj_name not in section.contours:

                continue

            ## Get objects alignment
            obj_alignment = series.getAttr(obj_name, "alignment")

            if not obj_alignment:
                
                tform = section.tform
                
            elif obj_alignment != "no-alignment":
                
                tform = section.tforms[obj_alignment]
                
            else:
                
                tform = None
            
            for trace in section.contours[obj_name]:

                # collect all points if generating a full surface
                obj_data[obj_name].addTrace(trace, snum, tform)

    # iterate through all objects and export 3D meshes

    for obj_name, obj_3D in obj_data.items():

        output_dir = Path(output_dir)
        output_file = output_dir / f"{obj_name}.{export_type}"

        if type(obj_3D) is Surface or type(obj_3D) is Spheres:

            obj_3D.exportTrimesh(
                output_file,
                export_type,
            )

    notify(f"Object(s) exported to directory:\n\n{output_dir.absolute()}\n")
