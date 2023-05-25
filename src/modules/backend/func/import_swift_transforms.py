import json
import numpy as np

from modules.datatypes import Series, Transform


def cafm_to_matrix(t):
    """Convert c_afm to Numpy matrix."""
    return np.matrix([[t[0][0], t[0][1], t[0][2]],
                      [t[1][0], t[1][1], t[1][2]],
                      [0, 0, 1]])


def cafm_to_sanity(t, dim):
    """Convert c_afm to something sane."""

    # swift transformation are inverted
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

    return t


def make_pyr_transforms(project_file, scale=1):
    """Return a list of PyReconstruct-formatted transformations."""

    with open(project_file, "r") as fp: swift_json = json.load(fp)

    scale_data = swift_json.get("data").get("scales").get(f'scale_{str(scale)}')
    
    data = scale_data.get("stack")
    height = scale_data.get('image_src_size')[1]

    swift_transforms = []

    for section in data:
        transform = section["alignment"]["method_results"]["cumulative_afm"]
        swift_transforms.append(transform)
    
    del(transform)

    recon_transforms = [cafm_to_matrix(t) for t in swift_transforms]
    recon_transforms = [cafm_to_sanity(t, dim=height) for t in recon_transforms]

    return recon_transforms


def transforms_as_strings(recon_transforms, output_file=None):
    """Print transformations to an output text file."""

    output = ''
    for i, t in enumerate(recon_transforms):
        string = f'{i} {t[0, 0]} {t[0, 1]} {t[0, 2]} {t[1, 0]} {t[1, 1]} {t[1, 2]}\n'
        output += string

    if output_file:
        with open(output_file, "w") as fp: fp.write(output)

    return output

        
def importSwiftTransforms(series : Series, project_fp : str):

    new_transforms = make_pyr_transforms(project_fp)
    new_transforms = transforms_as_strings(new_transforms)

    tforms = {}  # Empty dictionary to hold transformations
    
    for line in new_transforms.strip().split("\n"):
        
        nums = line.split()
        
        if len(nums) != 7:
            
            print("Incorrect transform file format")
            return
        
        try:
            
            if int(nums[0]) not in series.sections:
                print("Transform file section numbers do not correspond to this series")
                return
            
            tforms[int(nums[0])] = [float(n) for n in nums[1:]]
            
        except ValueError:
            
            print("Incorrect transform file format")
            return
        
    # set tforms
    for section_num, tform in tforms.items():
        
        section = series.loadSection(section_num)

        # multiply pixel translations by magnification of section
        tform[2] *= section.mag
        tform[5] *= section.mag

        section.tforms[series.alignment] = Transform(tform)

        section.save()
