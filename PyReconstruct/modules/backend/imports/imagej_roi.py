"""ImageJ .roi file."""

from typing import List, Tuple

import numpy as np
from scipy.interpolate import splprep, splev

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

        if self.closed and (not coords[0] == coords[1]):
            coords.append(coords[0])

        x = np.array([p[0] for p in coords])
        y = np.array([img_height - p[1] for p in coords])

        # Create a periodic spline representation (k=3 for cubic, s=0 for exact interpolation)
        tck, u = splprep([x, y], s=0, per=1, k=3)

        # Evaluate the spline at more points
        u_new = np.linspace(0, 1, 100)
        smooth_x, smooth_y = splev(u_new, tck)

        smooth_x = [x * mag for x in smooth_x] 
        smooth_y = [y * mag for y in smooth_y]

        return list(zip(smooth_x, smooth_y))

    
