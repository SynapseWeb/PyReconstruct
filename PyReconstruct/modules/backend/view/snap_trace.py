import numpy as np
from skimage.segmentation import active_contour
from skimage import filters

from PyReconstruct.modules.datatypes import Series, Section, Trace
from PyReconstruct.modules.backend.view import SectionLayer
from PyReconstruct.modules.calc import fieldPointToPixmap, pixmapPointToField
from PyReconstruct.modules.backend.view import optimizeSectionBC

def snapTrace(series : Series, section : Section, trace : Trace):
    # get window and pixmap dimensions
    x1, y1, x2, y2 = trace.getBounds()
    p = 0.2
    window = [x1 - p, y1 - p , x2-x1 + p*2, y2-y1 + p*2]
    pixmap_dim = (
        window[2] / section.mag / 2, 
        window[3] / section.mag / 2
    )

    # optimize the brightness and contrast (save the old values)
    b, c = section.brightness, section.contrast
    optimizeSectionBC(
        section,
        desired_std=100,
        window=window,
        lowest_res=False
    )

    # get the image
    slayer = SectionLayer(section, series)
    img = slayer.generateImageArray(pixmap_dim, window)
    gaussian = filters.gaussian(img, sigma=3, preserve_range=False)
    section.brightness, section.contrast = b, c  # reset the brightness and contrast

    # get the rough trace
    field_points = trace.points
    rough_trace = []
    for x, y in field_points:
        x, y = fieldPointToPixmap(x, y, window, pixmap_dim, section.mag)
        rough_trace.append((y, x))

    # run the activate_contour function
    snake = active_contour(
        image=gaussian,
        snake=np.array(rough_trace),
        alpha=0.01,
        beta=0,
        w_line=-1,
        w_edge=1,
        gamma=0.001,
        max_px_move=0.05,
        boundary_condition="periodic",
        max_num_iter=200
    )
    new_points = [
        pixmapPointToField(
            x, y, 
            pixmap_dim, 
            window, 
            section.mag
        ) for y, x in snake
    ]
    return new_points