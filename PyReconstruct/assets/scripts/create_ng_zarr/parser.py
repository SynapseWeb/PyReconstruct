"""Create neuroglancer-formatted zarrs from PyReconstruct jser files."""

import os
import argparse
import tomllib

def get_args ():
    """Get args for conversion."""

    parser = argparse.ArgumentParser(
        prog="ng-create-zarr",
        description=__doc__,
        epilog="example call: ng-create-zarr my_series.jser --groups dendrites spines",
    )

    ## Poitional args
    parser.add_argument("jser", type=str, nargs="?", help="Filepath of a valid jser file.")

    ## Optional args

    parser.add_argument(
        "--config",
        "-c",
        type=str,
        help="filepath to a toml config file"
    )

    parser.add_argument(
        "--start_section",
        "-s",
        type=int,
        default=None,
        help="the first section to include (default to second section in series to avoid calgrid)",
    )

    parser.add_argument(
        "--end_section",
        "-e",
        type=int,
        default=None,
        help="the last section to include (default last section in series)",
    )

    parser.add_argument(
        "--mag",
        "-m",
        type=float,
        default=0.002,
        help="output zarr lateral resolution (default %(default)s μm)",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Optional output path",
    )

    parser.add_argument(
        "--padding",
        "-p",
        type=int,
        default=50,
        help="padding (px) to include around group objects (default %(default)s px)",
    )

    parser.add_argument(
        "--groups",
        "-g",
        type=str,
        action="append",
        nargs="*",
        default=None,
        help="Object groups to include as labels (default %(default)s μm/vox)",
    )

    parser.add_argument(
        "--max_tissue",
        action="store_true",
        help="Inclue all possible tissue and black space",
    )

    args = parser.parse_args()

    ## Optional toml config file
    if args.config:
    
        with open(args.config, "rb") as fp:
            
            try:
                parser.set_defaults(**tomllib.load(fp))
            
            except tomllib.TOMLDecodeError:
                parser.error("Malformed toml config file.")
            
        if args.groups:
            parser.set_defaults(
                groups=None
            )  # override toml acting as defaults if --groups called
        
        args = parser.parse_args()

    if not args.jser or not os.path.exists(args.jser):
        parser.error("Please provide filepath to a valid jser.")

    return args


def parse_args(args):

    jser_fp = args.jser
    output_zarr = args.output
    start = args.start_section
    end = args.end_section
    mag = float(args.mag)
    padding = int(args.padding)
    max_tissue = bool(args.max_tissue)

    if start: start = int(start)
    if end: end = int(end)

    return jser_fp, output_zarr, start, end, mag, padding, max_tissue
