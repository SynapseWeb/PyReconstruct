from typing import Tuple, Union


def rgb_norm_1 (rgb: Tuple[Union[int, float]]):
    """Normalize rgb to 0-1 range."""

    r, g, b = [x/255 if x > 1 else x for x in rgb]
    return r, g, b


def rgb_norm_256 (rgb: Tuple[Union[int, float]]):
    """Normalize rgb to 0-1 range."""

    return tuple(int(e * 255) for e in rgb)


def is_light(color):
    """Determine if perceived color is light."""

    ## Normalize RGB to 0-1 if needed
    scale_256 = any([e > 1 for e in color])
    
    if scale_256:
        r, g, b = [x/255 for x in color]
    else:
        r, g, b = color

    ## Calculate perceived brightness
    brightness = (0.299*r + 0.587*g + 0.114*b)

    return brightness > 0.5

