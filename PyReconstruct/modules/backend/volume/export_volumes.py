"""Export 3D objects."""

from pathlib import Path
from typing import List

import numpy as np
import trimesh

from .objects_3D import Surface, Spheres, Contours

from PyReconstruct.modules.datatypes import Series
from PyReconstruct.modules.gui.utils import notify


def export3DObjects(series: Series, obj_names : list, output_dir : str, export_type: str, notify_user: bool = True) -> None:
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
            
            else:

                tform = section.tforms[obj_alignment]
            
            for trace in section.contours[obj_name]:

                ## Collect all points if generating full surface
                obj_data[obj_name].addTrace(trace, snum, tform)

    ## Iterate through objects and export 3D meshes

    output_directory = Path(output_dir)

    for obj_name, obj_3D in obj_data.items():

        output_file = output_directory / f"{obj_name}.{export_type}"

        if type(obj_3D) is Surface or type(obj_3D) is Spheres:

            obj_3D.exportTrimesh(
                output_file,
                export_type,
            )

    if notify_user:
        
        notify(f"Object(s) exported to directory:\n\n{output_directory.absolute()}\n")


def convert_vedo_to_tm(obj) -> trimesh.Trimesh:
    """Convert vtk/vedo meshes to trimesh meshes."""

    polydata = obj.msh.polydata()
    points = polydata.GetPoints()

    ## Scale cube be different yo
    if obj.name == "Scale Cube":

        n_points = points.GetNumberOfPoints()
        point_array = np.zeros((n_points, 3))

        for i in range(n_points):
            point_array[i] = points.GetPoint(i)

        mesh = trimesh.Trimesh(
            vertices=point_array,
            prcess=False
        )

        return mesh.convex_hull

    verts = np.array(
        [points.GetPoint(i) for i in range (points.GetNumberOfPoints())]
    )

    faces = []

    for i in range(polydata.GetNumberOfCells()):

        cell = polydata.GetCell(i)
        face = [cell.GetPointId(j) for j in range(cell.GetNumberOfPoints())]

        if len(face) == 3:  # make sure trianglulated

            faces.append(face)

    mesh = trimesh.Trimesh(
        vertices=verts,
        faces=np.array(faces)
    )

    return mesh


def return_mesh_mtl(obj) -> str:
    """Make mtl file string for an exported obj."""

    col_norm = list(
        map(lambda x: x/255, obj.color)
    )

    mtl_str = (
        f"newmtl {obj.name}\n"
        f"Ka {col_norm[0]} {col_norm[1]} {col_norm[2]}\n"
        f"Kd {col_norm[0]} {col_norm[1]} {col_norm[2]}\n"
        f"Ks 0.5 0.5 0.5\n"
        f"Ns 10.0\n"
    )

    return mtl_str


def combine_mtl_files(mtl_list: List[Path], combo_file: Path, remove: bool=True) -> None:
    """Combine multiple mtl files into a single file."""

    with (combo_file).open("w") as mtl_combo:

        for f in mtl_list:

            with f.open("r") as one_mtl:
                mtl_combo.write(one_mtl.read() + "\n")

            if remove:

                f.unlink()

    return None


def combine_obj_files(obj_list: List[Path], combo_file: Path, remove: bool=True) -> None:
    """Combine multiple obj files into a single file."""

    mtl_file = combo_file.with_suffix('.mtl')
    
    with combo_file.open("w") as obj_combo:

        pyrecon_plug = "# Exported from PyReconstruct 3D scene\n"
        mtl_info = f"mtllib {mtl_file.name}\n"

        obj_intro = pyrecon_plug
        
        if mtl_file.exists():
            obj_intro += mtl_info

        obj_combo.write(obj_intro)

    line_tracker = 0

    for f in obj_list:

        obj_lines = f.read_text().split("\n")
        del obj_lines[0:2]  # remove first two lines in obj file

        ## Adjust face indices
        obj_lines = list(
            map(lambda elem: alter_face_indices(elem, line_tracker), obj_lines)
        )

        with combo_file.open("a") as obj_combo:

            for line in obj_lines:
                obj_combo.write(line + "\n")
                
        n_verts = sum([l.startswith("v ") for l in obj_lines])
        line_tracker += n_verts

        if remove:
            
            f.unlink()

    return None


def alter_face_indices(obj_line, add):
    """Alter face indices when combining obj files."""

    if not obj_line.startswith("f "):

        return obj_line

    line_parts = obj_line.strip().split(" ")

    _, x, y, z = line_parts

    return f"f {int(x) + add} {int(y) + add} {int(z) + add}"
