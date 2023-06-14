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

    print(f'pre-scaled matrix: {t}')
    
    # Apply any scale ratio difference
    scale_martix = np.matrix([[scale_ratio, 0, 0],
                              [0, scale_ratio, 0],
                              [0, 0, 1]])

    t = np.matmul(scale_martix, t)

    print(f'post-scaled matrix: {t}')

    return t


def make_pyr_transforms(project_file, scale=1):
    """Return a list of PyReconstruct-formatted transformations."""

    with open(project_file, "r") as fp: swift_json = json.load(fp)

    scale = f'scale_{str(scale)}'
    scale_data = swift_json["data"]["scales"][scale]
    scale_data_1 = swift_json["data"]["scales"]["scale_1"]
    
    stack_data = scale_data.get("stack")
    
    img_height_1 = scale_data_1.get('image_src_size')[1]
    print(f'IMG HEIGHT SCALE 1: {img_height_1}')
    
    img_height = scale_data.get('image_src_size')[1]
    print(f'IMG HEIGHT OTHER SCALE: {img_height}')

    height_ratio = img_height_1 / img_height

    height_ratio = 1  # For now

    pyr_transforms = []

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

        
def importSwiftTransforms(series : Series, project_fp : str, scale : int = 1):

    new_transforms = make_pyr_transforms(project_fp, scale)
    new_transforms = transforms_as_strings(new_transforms)

    tforms = {}  # Empty dictionary to hold transformations
    
    for line in new_transforms.strip().split("\n"):
        
        nums = line.split()
        
        if len(nums) != 7:
            
            raise IncorrectFormatError(f"Project file (at index {nums[0]}) is not correct length")
        
        try:
            
            if int(nums[0]) not in series.sections:
                raise IncorrectSecNumError("Section numbers in project file do not correspond to current series.")
            
            tforms[int(nums[0])] = [float(n) for n in nums[1:]]
            
        except ValueError:
            
            raise IncorrectFormatError("Incorrect project file format.")
        
    # set tforms
    for section_num, tform in tforms.items():
        
        section = series.loadSection(section_num)

        # multiply pixel translations by magnification of section
        tform[2] *= section.mag
        tform[5] *= section.mag

        section.tforms[series.alignment] = Transform(tform)

        section.save()

    print("SWiFT transforms imported!")
