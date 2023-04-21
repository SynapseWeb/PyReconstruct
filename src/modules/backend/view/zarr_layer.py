import os
import zarr
import numpy as np
from skimage import color

from PySide6.QtCore import (
    Qt
)
from PySide6.QtGui import (
    QPixmap, 
    QImage, 
    QPainter, 
)
os.environ['QT_IMAGEIO_MAXALLOC'] = "0"  # disable max image size

from modules.datatypes import (
    Series,
    Section
)

from modules.calc import pixmapPointToField

class ZarrLayer():

    def __init__(self, series : Series):
        """Create the image field.

            Params:
                section (Section): the section object for the field
                series (Series): the series object
        """
        self.series = series
        if self.series.zarr_overlay_fp:
            self.loadZarrData()
        else:
            self.zarr = None
    
    def loadZarrData(self):
        """Load the relevant data from the zarr file."""
        self.zarr = zarr.open(self.series.zarr_overlay_fp)

        # check if labels or otherwise
        self.is_labels = (len(self.zarr.shape) == 3)

        # get relevant data from overlay zarr
        offset = self.zarr.attrs["offset"]
        resolution = self.zarr.attrs["resolution"]

        # get the relevant data from the raw in the zarr folder
        raw = zarr.open(os.path.join(
            os.path.dirname(self.series.zarr_overlay_fp),
            "raw"
        ))
        self.zarr_x, self.zarr_y = tuple(raw.attrs["window"][:2])
        self.zarr_s = raw.attrs["srange"][0]
        self.zarr_mag = raw.attrs["true_mag"]

        # modify attributes
        pixel_offset = [o / r for o, r in zip(offset, resolution)]
        field_offset = [p * self.zarr_mag for p in pixel_offset]
        self.zarr_x += field_offset[2]
        self.zarr_y += field_offset[1]
        self.zarr_s += pixel_offset[0]

        # defaults
        self.selected_ids = []

        # load colors
        if self.is_labels:
            unique = np.unique(self.zarr)
            self.colors = np.random.randint(
                256,
                size=(len(unique), 3)
            )
        # if self.is_labels:
        #     unique = np.unique(self.zarr)
        #     self.colors = dict(zip(
        #         unique,
        #         np.random.randint(
        #             256,
        #             size=(len(unique),3)
        #         )
        #     ))
    
    def selectID(self, pix_x, pix_y):
        """Select an ID from a user click."""

    
    def generateZarrLayer(self, section : Section, pixmap_dim : tuple, window : list) -> QPixmap:
        """Generate the zarr layer.
        
            Params:
                section (Section): the current section object
                pixmap_dim (tuple): the w and h of the main window
                window (list): the x, y, w, and h of the field window
            Returns:
                zarr_layer (QPixmap): the zarr layer
        """
        # return nothing if there is no zarr file
        if not self.zarr:
            return None
        
        if self.is_labels:
            bz, bh, bw = self.zarr.shape
        else:
            bz, bh, bw = self.zarr.shape[1:]
        
        # check if the section is within the range
        z = round(section.n - self.zarr_s)
        if not 0 <= z < bz:
            return None
        
        # save and unpack window and pixmap values
        self.pixmap_dim = pixmap_dim
        self.window = window
        pixmap_w, pixmap_h = tuple(pixmap_dim)
        window_x, window_y, window_w, window_h = tuple(window) 

        # scaling: ratio of screen pixels to actual image pixels (should be equal)
        x_scaling = pixmap_w / (window_w / section.mag)
        y_scaling = pixmap_h / (window_h / section.mag)
        # assert(abs(x_scaling - y_scaling) < 1e-6)
        self.zarr_scaling = x_scaling * self.zarr_mag / section.mag

        # calculate the coordinates to crop the image
        xmin = ((window_x - self.zarr_x) / self.zarr_mag)
        xmax = ((window_x + window_w - self.zarr_x) / self.zarr_mag)

        ymin = bh - ((window_y + window_h - self.zarr_y) / self.zarr_mag)
        ymax = bh - ((window_y - self.zarr_y) / self.zarr_mag)
        
        # calculate the shift in origin
        origin_shift = [
            window_x - self.zarr_x,
            (window_y + window_h) - self.zarr_y
        ]

        # space to insert if crop falls outside image
        blank_space = [0, 0]
        # space to append if crop falls outside image
        extra_space = [0, 0]

        # check if requested view is completely out of bounds
        oob = False
        oob |= xmin >= bw
        oob |= xmax <= 0
        oob |= ymin >= bh
        oob |= ymax <= 0
        # return nothing if coords are out of bounds
        if oob:
            return None

        # trim crop coords to be within image
        if xmin < 0:
            blank_space[0] = -xmin
            xmin = 0
        if ymin < 0:
            blank_space[1] = -ymin
            ymin = 0
        if xmax > bw:
            extra_space[0] = xmax - bw
            xmax = bw
        if ymax > bh:
            extra_space[1] = ymax - bh
            ymax = bh

        # crop image
        xmin, ymin, xmax, ymax = tuple(map(int, (xmin, ymin, xmax, ymax)))

        if self.is_labels:
            # zarr_crop = self.zarr[z, ymin:ymax, xmin:xmax]
            # zarr_crop_colors = np.ndarray(zarr_crop.shape + (3,), dtype=np.uint8)
            # for id in self.colors:
            #     zarr_crop_colors[zarr_crop == id] = self.colors[id]
            zarr_section = color.label2rgb(
                self.zarr[z,:,:],
                colors=self.colors
            ).astype(np.uint8)
            zarr_crop_colors = np.ascontiguousarray(zarr_section[ymin:ymax, xmin:xmax])
        else:
            zarr_crop = self.zarr[:3, z, ymin:ymax, xmin:xmax]
            zarr_crop_colors = np.ascontiguousarray(np.moveaxis(zarr_crop, 0, -1))
        im_crop = QImage(
            zarr_crop_colors.data,
            xmax-xmin,
            ymax-ymin,
            zarr_crop_colors.strides[0],
            QImage.Format.Format_RGB888
        )

        # make the crop the size of the screen
        im_scaled = im_crop.scaled(
            im_crop.width()*self.zarr_scaling, 
            im_crop.height()*self.zarr_scaling
        )
        for pair in (blank_space, extra_space, origin_shift):
            for i in range(len(pair)):
                pair[i] *= self.zarr_scaling

        # get padded pixmap dim
        padded_w = int(blank_space[0] + im_scaled.width() + extra_space[0] + 1)
        if padded_w < pixmap_dim[0]: padded_w = pixmap_dim[0]
        padded_h = int(blank_space[1] + im_scaled.height() + extra_space[1] + 1)
        if padded_h < pixmap_dim[1]: padded_h = pixmap_dim[1]

        # add blank space on each side
        zarr_layer = QPixmap(padded_w, padded_h)
        zarr_layer.fill(Qt.transparent)
        painter = QPainter(zarr_layer)
        painter.drawImage(
            blank_space[0],
            blank_space[1],
            im_scaled
        )
        painter.end()

        return zarr_layer

hash_colors = {}
def hashColor(id, selected_ids):
    """Return a color based on the id (rgb or primary)."""
    if id not in hash_colors:
        r = id % 6 + 1
        if r == 1:
            hash_colors[id] = (255, 0, 0)
        elif r == 2:
            hash_colors[id] = (0, 255, 0)
        elif r == 3:
            hash_colors[id] = (0, 0, 255)
        elif r == 4:
            hash_colors[id] = (0, 255, 255)
        elif r == 5:
            hash_colors[id] = (255, 0, 255)
        elif r == 6:
            hash_colors[id] = (255, 255, 0)
    c = hash_colors[id]
    if id in selected_ids:
        c = tuple([(n + 20 if n <= (255-20) else n) for n in c])
    return c

