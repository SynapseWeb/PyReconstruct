"""
Mask series images based on an object group.

Example usage: series-mask <jser> <group>

Optionally provide an argument to specify sections to include:

series-mask <jser> <groups> <sections>

"0", "0-2", "0,1,2" are all valid arguments. For example:

series-mask my_series.jser dendrites 0,2,4

Will mask only sections 0, 2, and 4. Not including the optional section argument
will mask all available images. (Keep in mind these are section numbers and not
necessarily section indices.) A warning is given if sections do not include
objects in the group and if specified sections are not available.
"""

import sys
import traceback
from pathlib import Path


import cv2
import zarr
import numpy as np
from colorama import Fore, Style
from colorama import just_fix_windows_console as windows_color_fix


class ImageNotFoundError(Exception):

    def __init__(self, img):
        msg = f"  {Fore.RED}ERROR{Style.RESET_ALL}: {img} does not exist."
        super().__init__(msg)


def issue_group_warning(group):

    print(f"  {Fore.YELLOW}WARNING{Style.RESET_ALL}: No objects in group \"{group}\" on this section.")


def validate_jser(filepath):
    """Validate jser provided by user."""
    
    jser = Path(filepath)
    
    if not jser.exists():
        
        print("Please provide filepath to an existing jser file.")
        sys.exit(1)
        
    else:
        
        return jser


def get_section_data(series, section_index):
    """Return data for a section."""

    sections = sorted(list(series.sections.keys()))
    return series.loadSection(sections[section_index])


def get_width_height_px(series, section_index):
    """Return the height and width of a section image."""

    section = get_section_data(series, section_index)

    if series.src_dir.endswith("zarr"):

        img_scale_1 = Path(series.src_dir) / "scale_1" / section.src

        if not img_scale_1 or not img_scale_1.exists():
            raise ImageNotFoundError(img_scale_1)
        
        h, w = zarr.open(img_scale_1).shape

    else:

        img_fp = Path(series.src_dir) / section.src

        if not img_fp or not img_fp.exists():
            raise ImageNotFoundError(img_fp)
        
        h, w, _ = cv2.imread(str(img_fp)).shape

    return w, h


def get_img_as_array(series, section_index):
    """Return the height and width of a section image."""

    section = get_section_data(series, section_index)

    if series.src_dir.endswith("zarr"):

        img_scale_1 = Path(series.src_dir) / "scale_1" / section.src

        if not img_scale_1 or not img_scale_1.exists() or not section.src:
            raise ImageNotFoundError(str(img_scale_1))
        
        img_arr = np.array(zarr.open(img_scale_1))

    else:

        img_fp = Path(series.src_dir) / section.src

        if not img_fp or not img_fp.exists() or not section.src:
            raise ImageNotFoundError(str(img_fp))
        
        img_arr = np.array(cv2.imread(str(img_fp)))

    return img_arr


def get_trace_data(series, section_index, group):
    """Get trace data pertaining to a group of objects."""

    section = get_section_data(series, section_index)
    traces = []

    for cname in series.object_groups.getGroupObjects(group):
        if cname in section.contours:
            traces += section.contours[cname].getTraces()

    return traces


def get_labels_as_arr(series, section_index, group):

    section = get_section_data(series, section_index)
    traces = get_trace_data(series, section_index, group)

    if len(traces) < 1: issue_group_warning(group)  # issue warning if necessary
    
    slayer = SectionLayer(section, series, load_image_layer=False)

    w, h = get_width_height_px(series, section_index)
    
    pixmap_dim = (w, h)
    window = (0, 0, w * section.mag, h * section.mag)

    return slayer.generateLabelsArray(
        pixmap_dim,
        window,
        traces,
        tform=Transform([1, 0, 0, 0, 1, 0])  ## TODO: This should work with None as well?
    )


def print_masked_sections(masked_sections, no_group_objs, group):
    """Mark blank sections with asterisk."""

    print(f"{Fore.GREEN}MASKED SECTIONS{Style.RESET_ALL}:\n")

    if masked_sections:
    
        masked_as_string = list(
            map(str, masked_sections)
        )

        def mark_with_asterisk(elem):
            if int(elem) in no_group_objs:
                return elem + "*"
            else:
                return elem
    
        if no_group_objs:
            
            masked_as_string = list(
                map(mark_with_asterisk, masked_as_string)
            )

        output_str = ", ".join(masked_as_string)
        print(f"{output_str}\n")

    else:

        print("No sections masked.\n")

    if no_group_objs:

        print(f"* = no objs in group \"{group}\" on this section\n")


def print_recap(series, group, tmp_dir, masked, no_group_objs, img_err_sections, other_errs, not_avail):

    notes_string = " MASKING NOTES "
    print(f"\n{notes_string:=^100}\n")

    print(
        f"Images for series \"{series.name}\" "
        f"masked by group \"{group}\" "
        f"and exported to: \n\n{tmp_dir.resolve()}\n"
    )

    print_masked_sections(masked, no_group_objs, group)

    if img_err_sections or other_errs:
        
        print(f"{Fore.RED}ERRORS{Style.RESET_ALL}: \n")

        if img_err_sections:
            
            print(
                f"Images for the following sections do not exist \n\n"
                f"{img_err_sections}\n"
            )

        if other_errs:
            
            print(
                f"The following sections produced errors (see errors above):\n\n"
                f"{other_errs}\n"
            )

    if not_avail or no_group_objs:

        print(f"{Fore.YELLOW}WARNINGS{Style.RESET_ALL}: \n")

        if not_avail:
        
            print(
                f"The following sections do not exist "
                f"and were not masked: \n\n{not_avail}\n"
            )

    end_string = " END OUTPUT "
    print(f"{end_string:=^100}\n")
    

if __name__ == "__main__":

    help_requested = any([elem in sys.argv for elem in ["--help", "-h"]])
    
    if len(sys.argv) == 1 or help_requested:

        print(__doc__)
        sys.exit()

    elif len(sys.argv) < 3:
        
        print(
            "Please provide all arguments: "
            "series-mask <jser> <group> [optional sections to include]"
        )
        
        sys.exit(1)

    start_string = " START MASKING "
    print(f"\n{start_string:=^100}\n")

    from PyReconstruct.modules.datatypes import Series
    from PyReconstruct.modules.backend.view import SectionLayer
    from PyReconstruct.modules.datatypes import Transform

    windows_color_fix()

    jser = validate_jser(sys.argv[1])
    group = sys.argv[2]

    try:
        
        restrict = sys.argv[3]

        if "-" in restrict:
            
            secs = restrict.split("-")
            restrict = range(int(secs[0]), int(secs[1]) + 1)
            restrict = list(restrict)
            
        elif "," in restrict:
            
            secs = restrict.split(",")
            restrict = list(map(int, secs))
            
        else:
            
            restrict = [int(restrict)]
        
    except IndexError:
        
        restrict = False
    
    print("Opening series...")
    series = Series.openJser(jser)

    tmp_dir = Path(f"{series.name}-masked-by-{group}")
    tmp_dir.mkdir(parents=True, exist_ok=True)

    masked_sections = []
    no_group_objs = []
    img_err_sections = []
    other_errs = []

    for i in range(len(series.sections)):

        section_n = get_section_data(series, i).n

        if restrict:
            if section_n not in restrict:
                continue

        print(f"\nWorking on section {section_n}...\n")

        try:

            print("  Making image array...")
            arr_image = get_img_as_array(series, i)

            print("  Making labels array...")
            arr_labels = get_labels_as_arr(series, i, group=group)
            
            if np.count_nonzero(arr_labels) == 0:
                no_group_objs.append(section_n)

            print("  Masking image array...")

            masked = cv2.bitwise_and(
                arr_image,
                arr_image,
                mask=arr_labels.astype(np.uint8)
            )

            tmp_fp = tmp_dir / f"{series.name}-{section_n}-masked.tiff"

            cv2.imwrite(str(tmp_fp), masked)

            print(f"  Section {section_n} masked and written to {tmp_fp.name}")

            masked_sections.append(section_n)

        except ImageNotFoundError as e:

            print(e)
            img_err_sections.append(section_n)

        except Exception as e:

            print(f"  {Fore.RED}ERROR{Style.RESET_ALL}: {type(e).__name__}\n")
            
            for line in traceback.format_exc().splitlines():
                print("  " + line)

            other_errs.append(section_n)

    print("\nMasking done.")

    secs_completed = masked_sections + img_err_sections + other_errs
            
    if restrict:
        
        not_avail = [elem for elem in restrict if elem not in secs_completed]
        
    else:

        all_secs = list(range(len(series.sections)))
        not_avail = [elem for elem in all_secs if elem not in secs_completed]

    print_recap(
        series,
        group,
        tmp_dir,
        masked_sections,
        no_group_objs,
        img_err_sections,
        other_errs,
        not_avail
    )

    series.close()
