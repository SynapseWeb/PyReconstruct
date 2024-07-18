import os
import zarr
import numpy as np

from PySide6.QtCore import (
    Qt
)
from PySide6.QtGui import (
    QPixmap, 
    QImage, 
    QPainter, 
)
os.environ['QT_IMAGEIO_MAXALLOC'] = "0"  # disable max image size

from PyReconstruct.modules.datatypes import (
    Series,
    Section
)

from PyReconstruct.modules.calc import colorize, pixmapPointToField

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
        group = zarr.open(self.series.zarr_overlay_fp)
        self.zarr = group[self.series.zarr_overlay_group]
        raw = group["raw"]
        self.raw_resolution = raw.attrs["resolution"]

        # check if labels or otherwise
        self.is_labels = (len(self.zarr.shape) == 3)

        # get relevant data from overlay zarr
        self.offset = self.zarr.attrs["offset"]
        self.resolution = self.zarr.attrs["resolution"]

        # get the relevant data from the raw in the zarr folder
        self.zarr_x, self.zarr_y = tuple(raw.attrs["window"][:2])
        self.zarr_s = raw.attrs["sections"][0]
        self.zarr_mag = raw.attrs["true_mag"] * (self.resolution[-1] / self.raw_resolution[-1])

        # modify attributes
        pixel_offset = [o / r for o, r in zip(self.offset, self.resolution)]
        field_offset = [p * self.zarr_mag for p in pixel_offset]
        self.zarr_x += field_offset[2]
        self.zarr_y += field_offset[1]
        self.zarr_s += pixel_offset[0]

        # defaults
        self.selected_ids = []

        # load colors
        if self.is_labels:
            self.id_colors = {}
    
    def getID(self, pix_x : int, pix_y : int):
        """Get an ID from screen pixel coordinates.
        
            Params: 
                pix_x (int): the x coord in screen pixels
                pix_y (int): the y coord in screen pixels
        """
        if not self.is_labels:
            return None
        
        # check if the section is within the range
        bz, bh, bw = self.zarr.shape
        z = round(self.section.n - self.zarr_s)
        if not 0 <= z < bz:
            return None
        
        # convert to field coordinates
        field_x, field_y = pixmapPointToField(
            pix_x, pix_y,
            self.pixmap_dim,
            self.series.window,
            self.section.mag
        )

        # get zarr coordinates from field coordinates
        image_x = round((field_x - self.zarr_x) / self.zarr_mag)
        image_y = bh - round((field_y - self.zarr_y) / self.zarr_mag)

        if not 0 <= image_x < bw:
            return None
        if not 0 <= image_y < bh:
            return None

        return self.zarr[z, image_y, image_x]

    def selectID(self, pix_x : int, pix_y : int):
        """Select the ID at a given screen coord.
        
            Params: 
                pix_x (int): the x coord in screen pixels
                pix_y (int): the y coord in screen pixels
        """
        label_id = self.getID(pix_x, pix_y)
        if label_id:
            if label_id in self.selected_ids:
                self.selected_ids.remove(label_id)
            else:
                self.selected_ids.append(label_id)
            return True
        return False

    def deselectAll(self):
        """Deselect all the IDs."""
        self.selected_ids = []
    
    def mergeLabels(self):
        """Merge the selected labels."""
        if not (self.is_labels and len(self.selected_ids) > 1):
            return
        
        min_id = min(self.selected_ids)
        self.selected_ids.remove(min_id)     

        for z in range(self.zarr.shape[0]):
            section = self.zarr[z]
            for label_id in self.selected_ids:
                section[section == label_id] = min_id
                self.zarr[z] = section        
        self.selected_ids = [min_id]
    
    def generateZarrLayer(self, section : Section, pixmap_dim : tuple, window : list) -> QPixmap:
        """Generate the zarr layer.
        
            Params:
                section (Section): the current section object
                pixmap_dim (tuple): the w and h of the main window
                window (list): the x, y, w, and h of the field window
            Returns:
                zarr_layer (QPixmap): the zarr layer
        """
        self.section = section

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
        self.series.window = window
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
            zarr_crop = self.zarr[z, ymin:ymax, xmin:xmax]
            # generate all labels
            zarr_crop_colors = np.ascontiguousarray(
                np.moveaxis(
                    np.array(
                        colorize(zarr_crop), dtype=np.uint8
                    ), 0, -1
                )
            )
            im_crop = QImage(
                zarr_crop_colors.data,
                xmax-xmin,
                ymax-ymin,
                zarr_crop_colors.strides[0],
                QImage.Format.Format_RGB888
            )
            # generate overlay for selected labels
            if self.selected_ids:
                zarr_crop_selected = np.zeros(zarr_crop.shape, dtype=np.uint8)
                for label_id in self.selected_ids:
                    zarr_crop_selected[zarr_crop == label_id] = 255
                im_crop_selected = QImage(
                    zarr_crop_selected.data,
                    xmax-xmin,
                    ymax-ymin,
                    zarr_crop_selected.strides[0],
                    QImage.Format.Format_Grayscale8
                )
                painter = QPainter(im_crop)
                painter.setOpacity(0.5)
                painter.drawImage(0, 0, im_crop_selected)
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