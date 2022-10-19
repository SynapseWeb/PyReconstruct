import os

from PySide6.QtCore import Qt, QRectF, QPoint
from PySide6.QtGui import (QPixmap, QImage, QPen, QColor, QTransform, QPainter, QPolygon)
os.environ['QT_IMAGEIO_MAXALLOC'] = "0"  # disable max image size

from modules.recon.section import Section

from modules.calc.pfconversions import fieldPointToPixmap

class ImageLayer():

    def __init__(self, section : Section, src_dir : str):
        """Create the image field.

            Params:
                section (Section): the section object for the field
                src_dir (str): the immediate directory for the images
        """
        self.section = section
        self.src_dir = src_dir
        self._transformImage()
    
    def _transformImage(self, load_image=True):
        """Apply the transform to the image."""
        # load transform
        t = self.section.tform
        image_tform = QTransform(t[0], -t[3], -t[1], t[4], t[2], t[5]) # changed positions for image tform
        if load_image:
            # load the image
            src_path = os.path.join(self.src_dir, os.path.basename(self.section.src))
            base_image = QImage(src_path)
            # get base corners
            bw, bh = base_image.width(), base_image.height()
            self.base_corners = [(0, 0), (0, bh), (bw, bh), (bw, 0)]
            # apply transform
            self.tformed_image = base_image.transformed(image_tform) # transform image
            # in order to place the image correctly in the field...
            self.tform_corners = self._calcTformCorners(base_image, image_tform)
        tform_origin = self.tform_corners[0] # find the coordinates of the tformed image origin (bottom left corner)
        x_shift = t[2] - tform_origin[0] * self.section.mag # calculate x translation for image placement in field
        y_shift = t[5] - (self.tformed_image.height() - tform_origin[1]) * self.section.mag # calculate y translation for image placement in field
        self.image_vector = x_shift, y_shift # store as vector
    
    def setSrcDir(self, src_dir : str):
        """Set the immediate source directory and reload image.
        
            Params:
                src_dir (str): the new directory for the images
        """
        self.src_dir = src_dir
        self._transformImage()
    
    def _calcTformCorners(self, base_pixmap : QPixmap, tform : QTransform) -> tuple:
        """Calculate the vector for each corner of a transformed image.
        
            Params:
                base_pixmap (QPixmap): untransformed image
                tform (QTransform): transform to apply to the image
            Returns:
                (tuple) the four corners (starting from bottom left moving clockwise)
        """
        base_coords = base_pixmap.size() # base image dimensions
        tform_notrans = tformNoTrans(tform) # get tform without translation
        height_vector = tform_notrans.map(0, base_coords.height()) # create a vector for base height and transform
        width_vector = tform_notrans.map(base_coords.width(), 0) # create a vector for base width and transform
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

    def changeTform(self, new_tform : list):
        """Set the transform for the image.
        
            Params:
                tform (list): the transform as a list of numbers
        """
        old_tform = self.section.tform
        # store new transform
        self.section.tform = new_tform
        # check if the old tform and new one differ only in translation
        same_shape = True
        for i in (0, 1, 3, 4):
            if abs(old_tform[i] - new_tform[i]) > 1e-6:
                same_shape = False
                break
        # if the two transformations do not have the same shape, reload image
        self._transformImage(load_image=(not same_shape))
    
    def changeBrightness(self, change : int):
        """Change the brightness of the section.
        
            Params:
                change (int): the degree to which brightness is changed
        """
        self.section.brightness += change
        if self.section.brightness > 255:
            self.section.brightness = 255
        elif self.section.brightness < -255:
            self.section.brightness = -255
    
    def changeContrast(self, change : float):
        """Change the contrast of the section.
        
            Params:
                change (float): the degree to which brightness is changed"""
        self.section.contrast = round(self.section.contrast + change, 1)
        if self.section.contrast > 4:
            self.section.contrast = 4
        elif self.section.contrast < 0:
            self.section.contrast = 0
    
    def _drawBrightness(self, image_layer):
        """Draw the brightness on the image field.
        
            Params:
                image_layer (QPixmap): the pixmap to draw brightness on
        """
        # get transform
        t = self.section.tform
        point_tform = QTransform(t[0], t[3], t[1], t[4], t[2], t[5])
        # establish first point
        brightness_poly = QPolygon()
        for p in self.base_corners:
            x, y = [n*self.section.mag for n in p]
            x, y = point_tform.map(x, y)
            x, y = fieldPointToPixmap(x, y, self.window, self.pixmap_dim, self.section.mag)
            brightness_poly.append(QPoint(x, y))
        # paint to image
        painter = QPainter(image_layer)
        if self.section.brightness >= 0:
            painter.setCompositionMode(QPainter.CompositionMode_Plus)
            brightness_color = QColor(*([self.section.brightness]*3))
        else:
            painter.setCompositionMode(QPainter.CompositionMode_Multiply)
            brightness_color = QColor(*([255+self.section.brightness]*3))
        painter.setPen(QPen(brightness_color, 0))
        painter.setBrush(brightness_color)
        painter.drawPolygon(brightness_poly)
    
    def _drawContrast(self, image_layer):
        """Draw the contrast on the image field.
        
            Params:
                image_layer (QPixmap): the pixmap to draw contrast on
        """
        # overlay image on itself for added contrast
        painter = QPainter(image_layer)
        painter.setCompositionMode(QPainter.CompositionMode_Overlay)
        for _ in range(int(self.section.contrast)):
            painter.drawPixmap(0, 0, image_layer)
        opacity = self.section.contrast % 1
        if opacity > 0:
            painter.setOpacity(opacity)
            painter.drawPixmap(0, 0, image_layer)
        painter.end()
    
    def generateImageLayer(self, pixmap_dim : tuple, window : list):
        """Generate the view seen by the user in the main window.
        
            Params:
                pixmap_dim (tuple): the w and h of the pixmap to be output
                window (list): the viewing window in the field (x, y, w, h)
        """
        self.pixmap_dim = pixmap_dim
        self.window = window
        # get dimensions of field window and pixmap
        window_x, window_y, window_w, window_h = tuple(window)
        pixmap_w, pixmap_h = tuple(pixmap_dim)

        # scaling: ratio of actual image dimensions to main window dimensions (should be equal)
        x_scaling = pixmap_w / (window_w / self.section.mag)
        y_scaling = pixmap_h / (window_h / self.section.mag)

        # create empty window
        image_layer = QPixmap(pixmap_w, pixmap_h)
        image_layer.fill(Qt.black)

        # get the coordinates to crop the image pixmap
        crop_left = (window_x - self.image_vector[0]) / self.section.mag
        left_empty = -crop_left if crop_left < 0 else 0
        crop_left = 0 if crop_left < 0 else crop_left

        crop_top = (window_y - self.image_vector[1] + window_h) / self.section.mag
        image_height = self.tformed_image.height()
        top_empty = (crop_top - image_height) if crop_top > image_height else 0
        crop_top = image_height if crop_top > image_height else crop_top
        crop_top = image_height - crop_top

        crop_right = (window_x - self.image_vector[0] + window_w) / self.section.mag
        image_width = self.tformed_image.width()
        crop_right = image_width if crop_right > image_width else crop_right

        crop_bottom = (window_y - self.image_vector[1]) / self.section.mag
        crop_bottom = 0 if crop_bottom < 0 else crop_bottom
        crop_bottom = image_height - crop_bottom

        crop_w = crop_right - crop_left
        crop_h = crop_bottom - crop_top

        # calculate corners of the original image
        corners = list(self.tform_corners)
        for i in range(len(corners)):
            p = corners[i]
            x = p[0]*x_scaling - window_x/self.section.mag*x_scaling
            y = p[1]*y_scaling + window_y/self.section.mag*y_scaling
            corners[i] = QPoint(x, y)

        # put the transformed image on the empty window
        painter = QPainter(image_layer)
        painter.drawImage(QRectF(left_empty * x_scaling, top_empty * y_scaling,
                            crop_w * x_scaling, crop_h * y_scaling),
                            self.tformed_image,
                            QRectF(crop_left, crop_top, crop_w, crop_h))
        painter.end()
        
        # draw in brightness
        self._drawBrightness(image_layer)
        
        # draw in contrast
        self._drawContrast(image_layer)

        return image_layer

def tformNoTrans(tform : QTransform) -> QTransform:
    """Return a transfrom without a translation component.
    
        Params:
            tform (QTransform): the reference transform
        Returns:
            (QTransform) the reference transform without a translation component
    """
    tform_notrans = (tform.m11(), tform.m12(), tform.m21(), tform.m22(), 0, 0)
    tform_notrans = QTransform(*tform_notrans)

    return tform_notrans
