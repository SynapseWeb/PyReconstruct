def pixmapPointToField(x : float, y : float, pixmap_dim : tuple, window : list, mag : float) -> tuple:
    """Convert main window pixmap coordinates to field window coordinates.
    
        Params:
            x (float): x-value for pixmap point
            y (float): y-value for pixmap point
            pixmap_dim (tuple): the w, h of pixmap
            window (list): the field viewing window
            mag (float): the image magnification (microns/pixel)
        Returns:
            (tuple) converted point in field coordinates
    """
    pixmap_w, pixmap_h = tuple(pixmap_dim)
    window_x, window_y, window_w, window_h = tuple(window)
    x_scaling = pixmap_w / (window_w / mag) # screen pixel to actual image pixel ratio
    y_scaling = pixmap_h / (window_h / mag) # should be the same number as previous
    # assert abs(x_scaling - y_scaling) < 1e-5
    x = x / x_scaling * mag + window_x
    y = (pixmap_h - y) / y_scaling * mag  + window_y

    return x, y

def fieldPointToPixmap(x : float, y : float, window : list, pixmap_dim : tuple, mag : float) -> tuple:
    """Convert field window coordinates to main window pixmap coordinates.
    
        Params:
            x (float): x-value for field point
            y (float): y-value for field point
        Returns:
            (tuple) converted point in pixmap coordinates
    """
    pixmap_w, pixmap_h = tuple(pixmap_dim)
    window_x, window_y, window_w, window_h = tuple(window)
    x_scaling = pixmap_w / (window_w / mag) # screen pixel to actual image pixel ratio
    y_scaling = pixmap_h / (window_h / mag) # should be the same number as previous
    # assert abs(x_scaling - y_scaling) < 1e-5
    x = (x - window_x) / mag * x_scaling
    y = (y - window_y)/ mag * y_scaling
    y = pixmap_h - y

    return round(x), round(y)