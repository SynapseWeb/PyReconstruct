import json
import numpy as np

from modules.datatypes import Series, Transform


class IncorrectFormatError(Exception):
    pass


class IncorrectSecNumError(Exception):
    pass


def cafm_to_matrix(t):
    """Convert c_afm to Numpy matrix."""
    return np.matrix([[t[0][0], t[0][1], t[0][2]],
                      [t[1][0], t[1][1], t[1][2]],
                      [0, 0, 1]])


def cafm_to_sanity(t, dim, scale_ratio=1):
    """Convert c_afm to something sane."""

    # Convert to matrix
    t = cafm_to_matrix(t)

    # SWiFT transformation are inverted
    t = np.linalg.inv(t)
    
    # Get translation of bottom left corner from img height (px)
    BL_corner = np.array([[0], [dim], [1]])  # original BL corner
    BL_translation = np.matmul(t, BL_corner) - BL_corner

    # Add BL corner translation to c_afm (x and y translations)
    t[0, 2] = BL_translation[0, 0] # x translation in px
    t[1, 2] = BL_translation[1, 0] # y translation in px

    # Flip y axis by changing signs of a2, b1, and b3
    t[0, 1] *= -1  # a2
    t[1, 0] *= -1  # b1
    t[1, 2] *= -1  # b3
    
    # Apply any scale ratio difference
    t[0, 2] *= scale_ratio
    t[1, 2] *= scale_ratio

    return t


def make_pyr_transforms(project_file, scale=1, cal_grid=False):
    """Return a list of PyReconstruct-formatted transformations."""

    with open(project_file, "r") as fp: swift_json = json.load(fp)

    scale = f'scale_{str(scale)}'
    scale_data = swift_json["data"]["scales"][scale]
    scale_data_1 = swift_json["data"]["scales"]["scale_1"]
    
    stack_data = scale_data.get("stack")
    
    img_height_1, img_width_1 = scale_data_1.get('image_src_size')
    img_height, img_width = scale_data.get('image_src_size')

    # Currently only the height in px is considered when scaling
    # Will need to understand if this changes with non-square images
    height_ratio = img_height_1 / img_height
    width_ratio = img_width_1 / img_width

    # Start with identity matrix if cal_grid included as section 0
    pyr_transforms = [np.identity(3)] if cal_grid else []

    for section in stack_data:
        
        # Get transform
        transform = section["alignment"]["method_results"]["cumulative_afm"]
        
        # Make sane
        transform = cafm_to_sanity(transform, dim=img_height, scale_ratio=height_ratio)
        
        # Append to list
        pyr_transforms.append(transform)
    
    del(transform)

    return pyr_transforms


def transforms_as_strings(recon_transforms, output_file=None):
    """Return transform matrices as string."""

    output = ''
    for i, t in enumerate(recon_transforms):
        string = f'{i} {t[0, 0]} {t[0, 1]} {t[0, 2]} {t[1, 0]} {t[1, 1]} {t[1, 2]}\n'
        output += string

    if output_file:
        with open(output_file, "w") as fp: fp.write(output)

    return output

        
def importSwiftTransforms(series: Series, project_fp: str, scale: int = 1, cal_grid: bool = False, log_event=True):

    new_transforms = make_pyr_transforms(project_fp, scale, cal_grid)
    new_transforms = transforms_as_strings(new_transforms)
    transforms_list = new_transforms.strip().split("\n")

    if len(transforms_list) != len(series.sections):
        raise IncorrectSecNumError("Mismatch between number of sections and number of transformations you are trying to import.")

    tforms = {}  # Empty dictionary to hold transformations
    
    for line in transforms_list:
        
        swift_sec, *matrix = line.split()
        
        if len(matrix) != 6:
            
            raise IncorrectFormatError(f"Project file (at index {swift_sec}) incorrect number of elements.")
        
        try:

            if int(swift_sec) not in series.sections:
                raise IncorrectSecNumError("Section numbers in project file do not correspond to current series.")

            current_tform = { int(swift_sec): [float(elem) for elem in matrix] }
            
            tforms.update(current_tform)
            
        except ValueError:
            
            raise IncorrectFormatError("Incorrect project file format.")
        
    # set tforms
    for section_num, tform in tforms.items():
        
        section = series.loadSection(section_num)

        # multiply pixel translations by magnification of section
        tform[2] *= section.mag
        tform[5] *= section.mag

        section.tform = Transform(tform)

        section.save()
    
    # log event
    if log_event:
        series.addLog(None, None, f"Import SWIFT transforms to alignment {series.alignment}")

    print("SWiFT transforms imported!")
