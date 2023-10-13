import os
import sys
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

from modules.datatypes import (
    Series,
    Section,
    Transform
)
from modules.calc import fieldPointToPixmap
from modules.constants import assets_dir

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
        self.is_scaled = False
        self.selected_scale = 1
        
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
                self.image_found = "scale_1" in self.zg and self.section.src in self.zg["scale_1"]
            else:
                self.image_found = False
            if self.image_found:
                self.image = self.zg["scale_1"][self.section.src]
                self.bh, self.bw = self.image.shape
                self.base_corners = [(0, 0), (0, self.bh), (self.bw, self.bh), (self.bw, 0)]
                self.image_found = True
                # get scales
                self.scales = []
                for g in self.zg:
                    if self.section.src in self.zg[g]:
                        self.scales.append(int(g.split("_")[-1]))
                self.scales.sort(reverse=True)
                if len(self.scales) > 1:
                    self.is_scaled = True
        
        # if saved as normal images
        else:
            src_path = os.path.join(self.series.src_dir, os.path.basename(self.section.src))
            self.image = QImage(src_path)
            if self.image.isNull():
                self.image_found = False
            else:
                self.bw, self.bh = self.image.width(), self.image.height()
                self.base_corners = [(0, 0), (0, self.bh), (self.bw, self.bh), (self.bw, 0)]
                self.image_found = True
    
    def setSrcDir(self, src_dir : str):
        """Set the immediate source directory and reload image.
        
            Params:
                src_dir (str): the new directory for the images
        """
        self.series.src_dir = src_dir
        self.loadImage()
    
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
    
    def setBrightness(self, b : int, log_event=True):
        """Set the brightness of the section."""
        self.section.brightness = b
        if self.section.brightness > 100:
            self.section.brightness = 100
        elif self.section.brightness < -100:
            self.section.brightness = -100
        
        if log_event:
            self.series.addLog(None, self.series.current_section, "Modify brightness/contrast")
    
    def setContrast(self, c : int, log_event=True):
        """Set the contrast of the section."""
        self.section.contrast = c
        if self.section.contrast > 100:
            self.section.contrast = 100
        elif self.section.contrast < -100:
            self.section.contrast = -100
        
        if log_event:
            self.series.addLog(None, self.series.current_section, "Modify brightness/contrast")
    
    def changeBrightness(self, change : int, log_event=True):
        """Change the brightness of the section.
        
            Params:
                change (int): the degree to which brightness is changed
        """
        self.setBrightness(self.section.brightness + change, log_event)
    
    def changeContrast(self, change : int, log_event=True):
        """Change the contrast of the section.
        
            Params:
                change (float): the degree to which contrast is changed"""
        self.setContrast(self.section.contrast + change, log_event)
    
    def _drawBrightness(self, image_layer):
        """Draw the brightness on the image field.
        
            Params:
                image_layer (QPixmap): the pixmap to draw brightness on
        """
        # paint to image
        painter = QPainter(image_layer)
        rgb = round(self.section.brightness * 255/100)
        # different modes for high and low brightness
        if self.section.brightness >= 0:
            painter.setCompositionMode(QPainter.CompositionMode_Plus)
            brightness_color = QColor(*([rgb]*3))
        else:
            painter.setCompositionMode(QPainter.CompositionMode_Multiply)
            brightness_color = QColor(*([255+rgb]*3))
        painter.setPen(QPen(brightness_color, 0))
        painter.setBrush(brightness_color)
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

    def generateImageLayer(self, pixmap_dim : tuple, window : list) -> QPixmap:
        """Generate the image layer.
        
            Params:
                pixmap_dim (tuple): the w and h of the main window
                window (list): the x, y, w, and h of the field window
            Returns:
                image_layer (QPixmap): the image laye
        """
        # save and unpack window and pixmap values
        self.pixmap_dim = pixmap_dim
        self.window = window
        pixmap_w, pixmap_h = tuple(pixmap_dim)
        window_x, window_y, window_w, window_h = tuple(window) 

        # scaling: ratio of screen pixels to actual image pixels (should be equal)
        x_scaling = pixmap_w / (window_w / self.section.mag)
        y_scaling = pixmap_h / (window_h / self.section.mag)
        self.scaling = x_scaling
        # assert(abs(x_scaling - y_scaling) < 1e-6)

        # return blank if image was not found
        if not self.image_found:
            blank_pixmap = QPixmap(pixmap_w, pixmap_h)
            blank_pixmap.fill(Qt.black)
            return blank_pixmap

        # get the applicable zarr scale if using zarr file for images
        scale_level = 1
        if self.is_zarr_file:
            for s in self.scales:
                if (1/self.scaling) > s:
                    scale_level = s
                    break

        # get vectors for four window corners
        window_corners = [
            [window_x, window_y],
            [window_x, window_y + window_h],
            [window_x + window_w, window_y + window_h],
            [window_x + window_w, window_y]
        ]
        
        # get transforms
        tform = self.section.tform

        # convert corners to image pixel coordinates
        for i in range(len(window_corners)):
            # apply inverse transform to window corners
            point = window_corners[i]
            point = list(tform.map(*point, inverted=True))
            # divide by image magnification
            point[0] /= self.section.mag
            point[1] /= self.section.mag
            # adjust y-coordinate
            point[1] = self.bh - point[1]
            window_corners[i] = point
        
        # get the bounding rectangle for the corners
        xmin, ymin, xmax, ymax = getBoundingRect(window_corners)
        
        # calculate the shift in origin
        origin_shift = [0, 0]
        origin_shift[0] = window_corners[1][0] - xmin
        origin_shift[1] = window_corners[1][1] - ymin

        # space to fill if crop falls outside image
        blank_space = [0, 0]
        # space to add if crop falls outside image
        extra_space = [0, 0]

        # check if requested view is completely out of bounds
        oob = False
        oob |= xmin >= self.bw
        oob |= xmax <= 0
        oob |= ymin >= self.bh
        oob |= ymax <= 0
        # return blank pixmap if coords are out of bounds
        if oob:
            blank_pixmap = QPixmap(pixmap_w, pixmap_h)
            blank_pixmap.fill(Qt.black)
            return blank_pixmap

        # trim crop coords to be within image
        if xmin < 0:
            blank_space[0] = -xmin
            xmin = 0
        if ymin < 0:
            blank_space[1] = -ymin
            ymin = 0
        if xmax > self.bw:
            extra_space[0] = xmax - self.bw
            xmax = self.bw
        if ymax > self.bh:
            extra_space[1] = ymax - self.bh
            ymax = self.bh

        # crop image and place in field
        xmin, ymin, xmax, ymax = tuple(
            map(
                int,
                (
                    xmin / scale_level,
                    ymin / scale_level,
                    xmax / scale_level,
                    ymax / scale_level
                )
            )
        )
        if self.is_zarr_file:
            if self.selected_scale != scale_level:
                self.image = self.zg[f"scale_{scale_level}"][self.section.src]
                self.selected_scale = scale_level
            zarr_saved = self.image[ymin:ymax, xmin:xmax]
            im_crop = QImage(
                zarr_saved.data,
                xmax-xmin,
                ymax-ymin,
                zarr_saved.strides[0],
                QImage.Format.Format_Grayscale8
            )
        else:
            crop_rect = QRect(
                xmin,
                ymin,
                xmax-xmin,
                ymax-ymin
            )
            im_crop = self.image.copy(crop_rect)

        # make the crop the size of the screen
        im_scaled = im_crop.scaled(im_crop.width()*self.scaling*scale_level, im_crop.height()*self.scaling*scale_level)
        blank_space[0] *= self.scaling
        blank_space[1] *= self.scaling
        extra_space[0] *= self.scaling
        extra_space[1] *= self.scaling
        origin_shift[0] *= self.scaling
        origin_shift[1] *= self.scaling

        # get padded pixmap dim
        padded_w = int(blank_space[0] + im_scaled.width() + extra_space[0] + 1)
        if padded_w < pixmap_dim[0]: padded_w = pixmap_dim[0]
        padded_h = int(blank_space[1] + im_scaled.height() + extra_space[1] + 1)
        if padded_h < pixmap_dim[1]: padded_h = pixmap_dim[1]

        # add blank space on each side
        im_padded = QPixmap(padded_w, padded_h)
        im_padded.fill(Qt.black)
        painter = QPainter(im_padded)
        painter.drawImage(
            blank_space[0],
            blank_space[1],
            im_scaled
        )
        painter.end()

        # transform the padded image
        image_tform = tform.imageTransform()
        im_tformed = im_padded.transformed(image_tform.getQTransform())

        # transform the origin shift coordinates
        origin_shift = list(image_tform.map(*origin_shift))
        # add to top right origin coordinate for transform
        top_left = self._calcTformCorners(im_padded, image_tform)[1]
        origin_shift[0] += top_left[0]
        origin_shift[1] += top_left[1]

        # crop the transformed image to screen dimensions
        image_layer_rect = QRect(
            round(origin_shift[0]),
            round(origin_shift[1]),
            *pixmap_dim
        )
        image_layer = im_tformed.copy(image_layer_rect)

        # create the brightness/contrast polygon (draws as a polygon over the image)
        self.bc_poly = QPolygon()
        for p in self.base_corners:
            x, y = [n*self.section.mag for n in p]
            x, y = tform.map(x, y)
            x, y = fieldPointToPixmap(x, y, self.window, self.pixmap_dim, self.section.mag)
            self.bc_poly.append(QPoint(x, y))
        # draw the brightness and contrast
        self._drawBrightness(image_layer)  # brightness first!
        self._drawContrast(image_layer)

        return image_layer
    
    def generateImageArray(self, pixmap_dim : tuple, window : list):
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
            window
        ).toImage()
        qimage = qimage.convertToFormat(QImage.Format.Format_RGBA8888)

        # convert the pixmap to a numpy array
        width = qimage.width()
        height = qimage.height()
        raw = np.frombuffer(qimage.bits(), np.uint8)
        raw = raw.reshape((height, width, 4))[:,:,0]
        arr = np.array(raw, dtype=np.uint8)

        return arr

def getBoundingRect(points : list):
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
