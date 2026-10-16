"""Export 3D objects."""

import csv
from pathlib import Path
from typing import List, Union

import numpy as np
import trimesh

from .objects_3D import Surface, Spheres, Contours, meshTform

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

    ## Collect 3D objects
    
    obj_data = {}

    for obj_name in obj_names:

        obj_data[obj_name] = get_3D_mesh(series, obj_name)

    reportSmoothingProblems([o.smoothing_problem for o in obj_data.values()], notify_user)

    ## Name the files, and refuse to save two objects to one file or over a file already there

    output_files = {}

    for obj_name, obj_3D in obj_data.items():

        if type(obj_3D) is Surface or type(obj_3D) is Spheres:

            # a smoothed mesh says so in its name, e.g. dendrite_smooth4.obj
            suffix = f"_{obj_3D.smoothing}" if obj_3D.smoothing else ""
            output_files[obj_name] = f"{obj_name}{suffix}.{export_type}"

    clash = findExportClash(output_files, output_dir)

    if clash:

        first, second, file_name = clash

        if first is None:
            message = (
                f"The objects were not exported: {second} would be saved as {file_name}, which is "
                "already in the folder. Move that file, or export to another folder."
            )

        else:
            message = (
                f"The objects were not exported: {first} and {second} would both be saved as "
                f"{file_name}. Rename one of them, or export them to separate folders."
            )

        if notify_user:
            notify(message)

        else:
            print(message)

        return

    ## Iterate through objects and export 3D meshes

    output_directory = Path(output_dir)

    for obj_name, file_name in output_files.items():

        obj_data[obj_name].exportTrimesh(
            output_directory / file_name,
            export_type,
        )

    if notify_user:
        
        notify(f"Object(s) exported to directory:\n\n{Path(output_directory).absolute()}\n")


def export3DData(series: Series, obj_names: list, output_fp: str, notify_user: bool=True) -> None:
    """Export quantitative data from meshes."""

    rows = [["Series", "Name", "MeshType", "SurfaceArea", "Volume", "ZtraceSmoothing"]]
    series_code = series.code

    errors = {}
    problems = []

    for obj in obj_names:

        try:

            obj_data = get_3D_mesh(series, obj)
            problems.append(obj_data.smoothing_problem)
            obj_type = type(obj_data).__name__.lower()
            tm = obj_data.generateTrimesh()

            surface_area = round(tm.area, 5)
            volume = round(tm.volume, 5)

            # the mesh is smoothed along a ztrace if ZtraceSmoothing is not blank
            rows.append([series_code, obj, obj_type, surface_area, volume, obj_data.smoothing])

        except Exception as e:

            errors[obj] = e

    reportSmoothingProblems(problems, notify_user)

    if not errors:

        # a field with a comma in it, e.g. the label smooth-hand,edit, is quoted
        with open(output_fp, "w", newline="") as fp:
            csv.writer(fp, lineterminator="\n").writerows(rows)

        if notify_user:
            notify(f"Data exported to:\n\n{Path(output_fp).absolute()}\n")

    if errors:

        print(errors)
        notify("There were errors exporting data from some or all of the objects. See console.")

        
def get_3D_mesh(series: Series, obj_name: str) -> Union[Surface, Spheres, Contours]:
    """Get mesh for an object."""

    ## Create initial 3D obj

    mode = series.getAttr(obj_name, "3D_mode")
            
    if mode == "surface":
        obj_data = Surface(obj_name, series)
            
    elif mode == "spheres":
        obj_data = Spheres(obj_name, series)
            
    elif mode == "contours":
        obj_data = Contours(obj_name, series)

    ## Shifts if the object is smoothed along a ztrace

    obj_data.offsets, obj_data.smoothing, obj_data.smoothing_problem = series.getZtraceSmoothing(obj_name)

    ## Iterate through sections and collect data

    for snum, section in series.enumerateSections(show_progress=False):

        ## Assume somewhat uniform section thickness
        # tform = section.tform

        if obj_name not in section.contours:

            continue

        ## Get alignment and smoothing shift
        tform = meshTform(series, obj_name, snum, section, obj_data.offsets)

        for trace in section.contours[obj_name]:

            ## Collect all points if generating full surface
            obj_data.addTrace(trace, snum, tform)
    
    return obj_data


def findExportClash(file_names: dict, folder=None):
    """Return the first two keys that would be exported to the same file, and that file, or None.

        A file already in the folder clashes as if exported first, under the key None.

        Params:
            file_names (dict): key : the file name it is exported under
            folder (str or Path): the folder it is exported to, or None to check the names only
    """
    exported = {}

    for key, file_name in file_names.items():

        folded = file_name.casefold()  # file names ignore case on macOS and Windows

        if folded in exported:
            return exported[folded], key, file_name

        if folder is not None and (Path(folder) / file_name).exists():
            return None, key, file_name

        exported[folded] = key

    return None


def reportSmoothingProblems(problems: list, notify_user: bool = True) -> None:
    """Say which objects were meshed as traced because their ztrace smoothing cannot be applied."""

    problems = [p for p in problems if p]

    if not problems:

        return

    message = "\n\n".join(problems)

    if notify_user:
        notify(message)

    else:
        print(message)


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
