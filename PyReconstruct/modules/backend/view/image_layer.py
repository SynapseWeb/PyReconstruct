import os
import math
import zarr
import subprocess
import numpy as np

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import (
    Qt,
    QPoint,
    QRect
)
from PySide6.QtGui import (
    QPixmap, 
    QImage, 
    QPen, 
    QColor, 
    QPainter, 
    QPolygon
)
os.environ['QT_IMAGEIO_MAXALLOC'] = "0"  # disable max image size

from PyReconstruct.modules.datatypes import (
    Series,
    Section,
    Transform
)
from PyReconstruct.modules.calc import fieldPointToPixmap
from PyReconstruct.modules.constants import assets_dir

class ImageLayer():

    def __init__(self, section : Section, series : Series):
        """Create the image field.

            Params:
                section (Section): the section object for the field
                series (Series): the series object
        """
        self.section = section
        self.series = series
        self.loadImage()
    
    def loadImage(self):
        """Load the image."""
        # get the image path
        self.is_zarr_file = self.series.src_dir.endswith("zarr")
        
        # if the image folder is a zarr file
        if self.is_zarr_file:
            if os.path.isdir(self.series.src_dir):
                self.zg = zarr.open(self.series.src_dir)
                # special expection: zarr is in previous format
                if self.section.src in self.zg:
                    # reorganize the zarr file (move images into scale_1 folder)
                    self.zg.create_group("scale_1", overwrite=True)
                    for g in self.zg:
                        if g != "scale_1":
                            self.zg.move(g, os.path.join("scale_1", g))
                # gather scales
                self.scales = self.section.zarr_scales
                if not self.scales:
                    self.image_found = False
                else:
                    self.image_found = True
                    self.scales.sort(reverse=True)
                    self.is_scaled = self.scales != [1]
                    self.selected_scale = self.scales[-1]
            else:
                self.image_found = False
            if self.image_found:
                self.image = self.zg[f"scale_{self.selected_scale}"][self.section.src]
                self.bh, self.bw = (n * self.selected_scale for n in self.image.shape)
                self.base_corners = [(0, 0), (0, self.bh), (self.bw, self.bh), (self.bw, 0)]
                self.image_found = True
        
        # if saved as normal images
        else:
            src_path = self.section.src_fp
            self.image = QImage(src_path)
            if self.image.isNull():
                self.image_found = False
            else:
                self.bw, self.bh = self.image.width(), self.image.height()
                self.base_corners = [(0, 0), (0, self.bh), (self.bw, self.bh), (self.bw, 0)]
                self.image_found = True
    
    def _calcTformCorners(self, base_pixmap : QPixmap, tform : Transform) -> tuple:
        """Calculate the vector for each corner of a transformed image.
        
            Params:
                base_pixmap (QPixmap): untransformed image
                tform (QTransform): transform to apply to the image
            Returns:
                (tuple) the four corners (starting from bottom left moving clockwise)
        """
        base_coords = base_pixmap.size() # base image dimensions
        height_vector = tform.map(0, base_coords.height()) # create a vector for base height and transform
        width_vector = tform.map(base_coords.width(), 0) # create a vector for base width and transform
        # calculate coordinates for the top left corner of image
        if height_vector[0] < 0:
            tl_x = -height_vector[0]
        else:
            tl_x = 0
        if width_vector[1] < 0:
            tl_y = -width_vector[1]
        else:
            tl_y = 0
        tl = (tl_x, tl_y)
        # calculate coordinates for the bottom left corner of the image
        bl_x = tl_x + height_vector[0]
        bl_y = tl_y + height_vector[1]
        bl = (bl_x, bl_y)
        # calculate coordinates for top right corner of the image
        tr_x = tl_x + width_vector[0]
        tr_y = tl_y + width_vector[1]
        tr = (tr_x, tr_y)
        # calculate coordinates for bottom right corner of the image
        br_x = bl_x + width_vector[0]
        br_y = bl_y + width_vector[1]
        br = (br_x, br_y)

        return bl, tl, tr, br
    
    def _drawBrightness(self, image_layer):
        """Draw the brightness on the image field.
        
            Params:
                image_layer (QPixmap): the pixmap to draw brightness on
        """
        # paint to image
        painter = QPainter(image_layer)
        b = self.section.brightness / 100
        # different modes for high and low brightness
        painter.setBrush(Qt.white if b >= 0 else Qt.black)
        painter.setOpacity(abs(b))
        painter.drawPolygon(self.bc_poly)
        painter.end()
    
    def _drawContrast(self, image_layer):
        """Draw the contrast on the image field.
        
            Params:
                image_layer (QPixmap): the pixmap to draw contrast on
        """
        painter = QPainter(image_layer)

        if self.section.contrast >= 0:
            overlays = self.section.contrast / 20
            # overlay image on itself for added contrast
            painter.setCompositionMode(QPainter.CompositionMode_Overlay)
            # draw the images n (int) times on itself
            for _ in range(int(overlays)):
                painter.drawPixmap(0, 0, image_layer)
            # draw another transparent image
            opacity = overlays % 1
            if opacity > 0:
                painter.setOpacity(opacity)
                painter.drawPixmap(0, 0, image_layer)
        else:
            # overlay gray on image for decreased contrast
            opacity = abs(self.section.contrast) / 100
            painter.setOpacity(opacity)
            gray = QColor(128, 128, 128)
            painter.setPen(QPen(gray, 0))
            painter.setBrush(gray)
            painter.drawPolygon(self.bc_poly)
        painter.end()

    def generateImageLayer(self, pixmap_dim : tuple, window : list, get_crop_only=False) -> QPixmap:
        """Generate the image layer.
        
            Params:
                pixmap_dim (tuple): the w and h of the main window
                window (list): the x, y, w, and h of the field window
                get_crop_only (bool): returns only the direct crop from the image (only for use with brightness/contrast functions)
            Returns:
                image_layer (QPixmap): the image laye
        """
        # set attrs
        self.series.window = window
        self.pixmap_dim = pixmap_dim

        # return blank if image was not found
        if not self.image_found:
            blank_pixmap = QPixmap(*pixmap_dim)
            blank_pixmap.fill(Qt.black)
            return blank_pixmap

        # setup
        tform = self.section.tform
        mag = self.section.mag
        wx, wy, ww, wh = tuple(self.series.window)
        pmw, pmh = tuple(self.pixmap_dim)
        iw, ih = self.bw, self.bh
        s = self.scaling = pmw / (ww / mag)

        # step 0: get the applicable zarr scale if using zarr file for images
        if self.is_zarr_file:
            scale_level = self.scales[-1]
            for scale in self.scales[:-1]:
                if (1/self.scaling) > scale:
                    scale_level = scale
                    break
            if self.selected_scale != scale_level:
                self.image = self.zg[f"scale_{scale_level}"][self.section.src]
                self.selected_scale = scale_level
        else:
            scale_level = 1
        

        # step 1: get the polygon for the window
        poly_window = [
            (wx, wy),
            (wx, wy + wh),
            (wx + ww, wy + wh),
            (wx + ww, wy)
        ]

        # step 2: untransform the window poly
        utf_poly_window = tform.map(poly_window, inverted=True)

        # step 3: convert to pixel coordinates
        utf_pixel_poly_window = [(x / mag, y / mag) for x, y in utf_poly_window]

        # step 4: get bounds to crop image
        bounds = getBounds(utf_pixel_poly_window)

        # step 5: adjust bounds to image dimensions and get necessary filling
        bounds, filling = adjustBounds(bounds, iw, ih)
        # check if completely out of bounds
        if bounds is None:
            blank_pixmap = QPixmap(pmw, pmh)
            blank_pixmap.fill(Qt.black)
            return blank_pixmap
        # unpack values otherwise
        xmin, ymin, xmax, ymax = bounds
        xminp, yminp, xmaxp, ymaxp = filling
        
        # step 6: get crop from image
        if self.is_zarr_file:
            # scale the cropping values accordingly
            xmins, ymins, xmaxs, ymaxs = (round(n / scale_level) for n in bounds)
            ihs = round(ih / scale_level)
            zarr_saved = self.image[
                ihs - ymaxs: ihs - ymins,
                xmins:xmaxs
            ]
            im_crop = QImage(
                zarr_saved.data,
                xmaxs-xmins,
                ymaxs-ymins,
                zarr_saved.strides[0],
                QImage.Format.Format_Grayscale8
            )
        else:
            crop_rect = QRect(
                xmin,
                ih-ymax,
                xmax-xmin,
                ymax-ymin
            )
            im_crop = self.image.copy(crop_rect)
        
        if get_crop_only:  # only for use with brightness/contrast functions
            return QPixmap.fromImage(im_crop)
        
        # setp 7: scale the cropped image
        im_scaled = im_crop.scaled(
            im_crop.width() * s * scale_level,
            im_crop.height() * s * scale_level
        )
        
        # step 8: fill the image (continue to account for scaling)
        im_filled = QPixmap(
            (xminp + (xmax - xmin) + xmaxp) * s,
            (ymaxp + (ymax - ymin) + yminp) * s
        )
        im_filled.fill(Qt.black)
        painter = QPainter(im_filled)
        painter.drawImage(
            xminp * s,
            ymaxp * s,
            im_scaled
        )
        painter.end()

        # step 9: transform the filled image
        im_tformed = im_filled.transformed(
            tform.imageTransform().getQTransform()
        )

        # step 10: rip the pixmap from the transformed image
        im_ripped = im_tformed.copy(
            (im_tformed.width() - pmw) / 2,
            (im_tformed.height() - pmh) / 2,
            pmw,
            pmh
        )
        
        # step 11: add blank space to account for rounding errors
        if (im_ripped.width(), im_ripped.height()) != pixmap_dim:
            image_layer = QPixmap(*pixmap_dim)
            image_layer.fill(Qt.black)
            painter = QPainter(image_layer)
            painter.drawPixmap(0, 0, im_ripped)
            painter.end()
        else:
            image_layer = im_ripped
        
        # step 12: draw brightness and contrast
        # create the brightness/contrast polygon (draws as a polygon over the image)
        self.bc_poly = QPolygon()
        for x, y in self.base_corners:
            x, y = (x * mag, y * mag)
            x, y = tform.map(x, y)
            x, y = fieldPointToPixmap(x, y, self.series.window, self.pixmap_dim, self.section.mag)
            self.bc_poly.append(QPoint(x, y))
        self._drawBrightness(image_layer)
        self._drawContrast(image_layer)

        return image_layer
    
    def generateImageArray(self, pixmap_dim : tuple, window : list, get_crop_only=False):
        """Generate the image layer.
        
            Params:
                pixmap_dim (tuple): the w and h of the 2D array
                window (list): the x, y, w, and h of the field window
            Returns:
                (numpy.ndarray) the image as a numpy array
        """
        # generate the qimage from pixmap
        qimage = self.generateImageLayer(
            pixmap_dim,
            window,
            get_crop_only
        ).toImage()
        qimage = qimage.convertToFormat(QImage.Format.Format_RGBA8888)


        # convert the pixmap to a numpy array
        width = qimage.width()
        height = qimage.height()
        raw = np.frombuffer(qimage.bits(), np.uint8)
        raw = raw.reshape((height, width, 4))[:,:,0]
        arr = np.array(raw, dtype=np.uint8)

        return arr

def getBounds(points : list):
    """Get the bounding rectangle and shift in origin for a set of points.
    
            Params:
                points (list): a list of points
            Returns:
                (tuple): xmin, ymin, xmax, ymax
    """
    xmin = points[1][0]
    xmax = points[1][0]
    ymin = points[1][1]
    ymax = points[1][1]
    for point in points:
        x, y = point
        if x < xmin:
            xmin = x
        if x > xmax: xmax = x
        if y < ymin:
            ymin = y
        if y > ymax: ymax = y
    
    return xmin, ymin, xmax, ymax

def adjustBounds(bounds, w, h):
    """Adjust the bounds to a specific width and height."""
    xmin, ymin, xmax, ymax = tuple(bounds)

    if xmin > w:
        return None, None
    elif xmin < 0:
        xmin_filling = 0 - xmin
        xmin = 0
    else:
        xmin_filling = 0
    
    if ymin > h:
        return None, None
    elif ymin < 0:
        ymin_filling = 0 - ymin
        ymin = 0
    else:
        ymin_filling = 0
    
    if xmax < 0:
        return None, None
    elif xmax > w:
        xmax_filling = xmax - w
        xmax = w
    else:
        xmax_filling = 0
    
    if ymax < 0:
        return None, None
    elif ymax > h:
        ymax_filling = ymax - h
        ymax = h
    else:
        ymax_filling = 0

    return (
        tuple(round(n) for n in (xmin, ymin, xmax, ymax)),
        tuple(round(n) for n in (xmin_filling, ymin_filling, xmax_filling, ymax_filling))
    )
