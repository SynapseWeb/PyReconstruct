"""Utility functions for labels to contours conversion."""


import sys
import shutil
from pathlib import Path
from typing import Union, List, Tuple
from multiprocessing import Pool, Manager

from PyReconstruct.modules.backend.autoseg.conversions import importSection

def print_flush(s: str):
    """Correct I/O buffering."""

    print(s, flush=True)


def print_help(doc_string: str, n_args: int) -> None:
    """Print help if necessary"""

    help_req = any([elem in sys.argv for elem in ["--help", "-h"]])

    ## Print help
    if help_req or len(sys.argv) == 1:
        
        print(doc_string)
        sys.exit()

    ## Print warning
    elif len(sys.argv[1:]) < n_args:
        
        print(
            "Please provide all arguments: "
            "ng-make-contours <zarr> <labels> <jser>"
        )
        
        sys.exit(1)

    else:

        return None


def validate_jser(jser_fp: str) -> bool:
    """Validate jser filepath."""

    jser_path = Path(jser_fp)
    
    path_exists = jser_path.exists()
    correct_ext = jser_path.suffix == ".jser"
    
    return all([path_exists, correct_ext])


def validate_zarr(zarr_fp: str) -> bool:
    """Validate jser filepath."""

    zarr_path = Path(zarr_fp)
    
    path_exists = zarr_path.exists()
    correct_ext = zarr_path.suffix == ".zarr"
    
    return all([path_exists, correct_ext])


def validate_files(zarr_fp, jser_fp) -> Union[List[str], bool]:
    """Validate files."""

    return validate_jser(jser_fp) and validate_zarr(zarr_fp)


def get_invalid_files(zarr_fp, jser_fp) -> List[str]:
    """Return list of invalid files."""

    invalid: List[str] = []

    if not validate_jser(jser_fp): invalid.append(jser_fp)
    if not validate_zarr(zarr_fp): invalid.append(zarr_fp)
    
    return invalid


def validate_input() -> Union[None, Tuple[str]]:
    """Validate all file input."""

    zarr_fp, jser_fp, *_ = sys.argv[1:]

    if not validate_files(zarr_fp, jser_fp):
        invalid_files = get_invalid_files(zarr_fp, jser_fp)
        print("\nThe following files do not exist or are not valid:\n")
        for f in invalid_files: print(f)
        print("\nExiting.\n")
        
        sys.exit(1)

    else:

        return zarr_fp, jser_fp


def make_jser_copy(jser_fp: str, amend_text: str="_with_labels") -> str:
    """Make a copy of a jser file and amend filename."""

    jser_path = Path(jser_fp)
    new_name = jser_path.stem + amend_text + ".jser"

    copy_path = jser_path.with_name(new_name)

    shutil.copy(jser_path, copy_path)

    return str(copy_path)


def get_zarr_groups(zarr_fp: str) -> List[str]:
    """Get zarr label groups."""

    return [d.name for d in Path(zarr_fp).iterdir() if d.name.startswith("labels")]

        
def process_section(args):
    # Unpack arguments
    zg, g, snum, series, counter_dict, total = args
    
    # Your original function
    result = importSection(zg, g, snum, series)
    
    # Update progress
    counter_dict['value'] += 1
    percent = (counter_dict['value'] / total) * 100
    sys.stdout.write(f"\rProgress: {percent:.1f}% ({counter_dict['value']}/{total})")
    sys.stdout.flush()
    
    return result


def parallel_import_sections(zg, g, start, max_secs, series, num_workers=None):
    # Calculate total iterations
    total = max_secs - start + 1
    section_range = range(start, max_secs + 1)
    
    with Manager() as manager:
        counter_dict = manager.dict({'value': 0})
        
        # Create argument tuples for each section
        args_list = [(zg, g, snum, series, counter_dict, total) for snum in section_range]
        
        # Process in parallel
        with Pool(processes=num_workers) as pool:
            results = pool.map(process_section, args_list)
    
    sys.stdout.write(f"\rProgress: 100.0% ({total}/{total})")
    sys.stdout.flush()
    print()  # New line after progress bar
    
    return results

