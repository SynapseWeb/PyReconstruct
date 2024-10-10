"""Grab example data from a remote server."""


from pathlib import Path
from typing import List
import numpy as np


def get_remote_vol(address: str,
                   roi: List[List[int]]):
    """Get remotely hosted volume as a CloudVolume cutout."""

    from cloudvolume import CloudVolume
    from cloudvolume.volumecutout import VolumeCutout

    vol = CloudVolume(address, mip=0, use_https=True)

    roi = list(
        map(lambda x: range(x[0], x[1]), roi)
    )
    
    return vol[roi[0], roi[1], roi[2]]


def save_vol_as_tifs(cutout,
                     output_dir: [str, Path]=".",
                     output_prefix: str="layer") -> bool:
    """Save CloudVolume cutout as tif stack."""

    import tifffile

    if isinstance(output_dir, str):
        output_dir = Path(output_dir)

    output_dir = str(output_dir.resolve())

    for z in range(cutout.shape[2]):

        layer = cutout[:, :, z]
        filename = f"{output_dir}/{output_prefix}_{z:04d}.tif"
        
        tifffile.imwrite(filename, np.transpose(layer))

    return True

    
def download_vol_as_tifs(address:str,
                         roi: List[List[int]],
                         output_dir: [str, Path]=".",
                         output_prefix: str="layer") -> bool:
    """Download remotely hosted volume as a tif stack."""

    cutout = get_remote_vol(address, roi)

    return save_vol_as_tifs(
        cutout,
        output_dir=output_dir,
        output_prefix=output_prefix
    )

