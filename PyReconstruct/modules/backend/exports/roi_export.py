"""ImageJ .roi file exporter."""

from pathlib import Path
from typing import Union, List, Tuple

from PyReconstruct.modules.backend.imports.mod_imports import modules_available
from PyReconstruct.modules.datatypes import Trace


coordinates = List[Tuple[float, float]]
filepath = Union[str, Path]


class RoiExporter:

    def __init__(self, trace: Trace, mag: float, img_height: int):

        if not modules_available("roifile"):
            return

        import roifile
        self.roi_mod = roifile

        self.trace = trace
        self.coords = self.get_coords(mag, img_height)
        self.roi = self.get_roi()

    def export_roi(self, directory: filepath) -> None:
        """Export an ImageJ .roi file to a directory."""

        if not isinstance(directory, Path):
            directory = Path(directory)

        ## Assume each trace uniquely named for now
        output_fp = directory / f"{self.trace.name}-exported.roi"

        self.roi.tofile(output_fp)

        return None

    def get_roi(self): 
        """Get an ImageJ roi object."""

        roi = self.roi_mod.ImagejRoi.frompoints(self.coords)
        
        roi.roitype = self.roi_mod.ROI_TYPE.POLYGON if self.trace.closed else self.roi_mod.ROI_TYPE.FREEHAND
        roi.name = self.trace.name

        return roi

    def get_coords(self, mag, img_height) -> coordinates:
        """Get coordinates as pixels."""

        coords = self.trace.asPixels(mag, img_height, subpix=True)

        return [
            (round(x, 3), round(y, 3)) for x, y in coords
        ]

