import os
import cv2
import zarr
import numpy as np

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
    if abs(current_mean) > 1e-6:
        brightness = ((desired_mean - current_mean) / current_mean) * 100
        brightness = max(-100, min(100, round(brightness)))
    else:
        brightness = None
    if abs(current_std) > 1e-6:
        contrast = ((desired_std / current_std) - 1) * 20
        contrast = max(-100, min(100, round(contrast)))
    else:
        contrast = None
    
    return brightness, contrast

def optimizeSectionBC(section : Section, desired_mean=128, desired_std=60, window=None, lowest_res=True):
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
        try:
            if os.path.isfile(fp):
                image = cv2.imread(fp, cv2.IMREAD_GRAYSCALE)
            else:  # get the smallest image if using a zarr
                if lowest_res:
                    scale_zg = f"scale_{max(section.zarr_scales)}"
                else:
                    scale_zg = f"scale_{min(section.zarr_scales)}"
                fp = os.path.join(
                    section.series.src_dir,
                    scale_zg,
                    section.src
                )
                image = zarr.open(fp, "r")[:]
            cv2.resize(image, (1024, 1024))
        except:
            print(f"Image at {fp} is corrupt. Skipping...")
            return
    else:
        slayer = SectionLayer(section, section.series)
        pixmap_dim = round(window[2] / section.mag), round(window[3] / section.mag)
        b, c = section.brightness, section.contrast
        section.brightness, section.contrast = 0, 0  # reset the brightness and contrast
        image = slayer.generateImageArray(pixmap_dim, window, get_crop_only=True)
        section.brightness, section.contrast = b, c

    # get desired brightness and contrast
    new_brightness, new_contrast = adjustPixelsToStats(
        image,
        desired_mean,
        desired_std
    )
    if new_brightness is not None:
        section.brightness = new_brightness
    if new_contrast is not None:
        section.contrast = new_contrast
    
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
    
        

