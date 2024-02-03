import cv2
import os

from PyReconstruct.modules.datatypes import Series, Section
from .section_layer import SectionLayer

# just here for reference, not actually used
def applyContrastAndBrightness(pixel : int, brightness : int, contrast : int):
    """Apply brightness and contrast to a single pixel.
    
        Params:
            pixel (int): the pixel value (0-255)
            brightness (int): the brightness adjustment (-100-100)
            contrast (int): the contrast adjustment (-100-100)
    """
    # apply brightness
    if brightness >= 0:
        pixel += (255 - pixel) * (brightness / 100)
    else:
        pixel += (pixel) * (brightness / 100)
    
    # apply contrast
    if contrast >= 0:
        pixel = (pixel - 128) * (contrast / 20 + 1) + 128
    else:
        pixel = (pixel - 128) * (1 - abs(contrast) / 100) + 128
    
    # round and clamp pixel value
    pixel = max(0, min(255, round(pixel)))

import numpy as np

def adjustPixelsToStats(image, desired_mean, desired_std):
    """Adjust a set of pixels to have the desired mean and standard deviation.

    Params:
        image (array): image as numpy array
        desired_mean (float): The target mean for the adjusted pixels.
        desired_std (float): The target standard deviation for the adjusted pixels.

    Returns:
        brightness (float): The calculated brightness adjustment (-100 to 100).
        contrast (float): The calculated contrast adjustment (-100 to 100).
    """
    # Calculate the current mean and standard deviation of the input pixels
    current_mean = np.mean(image)
    current_std = np.std(image)

    # Calculate the required brightness and contrast adjustments
    brightness = ((desired_mean - current_mean) / current_mean) * 100
    contrast = ((desired_std / current_std) - 1) * 20

    # Ensure that brightness and contrast are within the valid range
    brightness = max(-100, min(100, round(brightness)))
    contrast = max(-100, min(100, round(contrast)))

    return brightness, contrast

def optimizeSectionBC(section : Section, desired_mean=128, desired_std=60, window=None):
    """Optimize the brightness and contrast of the image for a single section.
    
        Params:
            section (Section): the section to optimize the brightness and contrast for
            desired_mean (int): the desired pixel average
            desired_std (float): the desired pixel standard deviation
            window (list): the x, y, w, h window (None if using full images)
    """
    # make sure the image exists
    fp = section.src_fp
    if not (os.path.isfile(fp) or os.path.isdir(fp)):
        return
    
    # get the image array
    if window is None:
        image = cv2.imread(fp)
    else:
        slayer = SectionLayer(section, section.series)
        pixmap_dim = round(window[2] / section.mag), round(window[3] / section.mag)
        section.brightness, section.contrast = 0, 0  # reset the brightness and contrast
        image = slayer.generateImageArray(pixmap_dim, window)

    # get desired brightness and contrast
    section.brightness, section.contrast = adjustPixelsToStats(
        image,
        desired_mean,
        desired_std
    )
    
def optimizeSeriesBC(series : Series, desired_mean=128, desired_std=60, section_nums=None, window=None):
    """Optimize the brightness and contrast of the images for a series.
    
        Params:
            series (Series): the series to optimize the brightness and contrast for
            desired_mean (int): the desired pixel average
            desired_std (float): the desired pixel standard deviation
            section_nums (list): the section numbers to optimize
            window (list): the x, y, w, h window (None if using full images)
    """
    for snum, section in series.enumerateSections():
        if section_nums is not None and snum in section_nums:
            optimizeSectionBC(section, desired_mean, desired_std, window)
            section.save()
    
        

