"""ImageJ .roi file."""

from typing import List, Tuple
from .mod_imports import modules_available


class Roi:

    def __init__(self, roi_fp):

        if not modules_available("roifile"):
            return
        
        import roifile

        self.roi_fp = roi_fp
        self.roi = roifile.ImagejRoi.fromfile(roi_fp)
        self.closed = self.trace_closed_p()

    def trace_closed_p(self) -> bool:
        """Return true if trace closed else false."""

        roi_closed_types = [0, 1, 2, 3, 9, 10]

        if self.roi.roitype in roi_closed_types:
            return True
        else:
            return False

    def get_field_coordinates(self, img_height: int, mag: float) -> List[Tuple[float]]:
        """Return field coordinates of roi trace."""

        coords = self.roi.coordinates().tolist()
        return [(x * mag, (img_height - y) * mag) for (x, y) in coords]  # flip y
