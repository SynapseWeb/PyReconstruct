"""
Insert labels as contours into a PyReconstruct .jser file.

Usage: ng-make-contours <zarr> <jser>
"""

from PyReconstruct.modules.datatypes.series import Series

from PyReconstruct.modules.backend.autoseg.conversions import getLabelsToObjectsData, importSection

from PyReconstruct.assets.scripts.contours_from_labels.utils import (
    get_zarr_groups,
    make_jser_copy,
    parallel_import_sections,
    print_help,
    validate_input,
)


if __name__ == "__main__":

    print_help(__doc__, 2)
    zarr_fp, jser_fp, *_ = validate_input()

    ## Make jser copy for contour data
    new_jser = make_jser_copy(jser_fp)
    series = Series.openJser(new_jser)

    ## Iterate through groups and import labels
    for g in get_zarr_groups(zarr_fp):

        print(f"Working on group {g}...")
        
        zg, secs, start = getLabelsToObjectsData(zarr_fp, g)
        end = max(secs)

        results = parallel_import_sections(
            zg, g, start, end, series, num_workers=4
        )

    ## Save and close series
    series.saveJser()
    series.close()

    ## Bask in glory
    print(f"Labels imported into {new_jser}")
