import numpy as np
from scipy.fftpack import fft2, ifft2


def correlate(image1: np.ndarray, image2: np.ndarray) -> tuple:
    """
    Compute correlation between two images using FFT
    
    Args:
    image1 (np.ndarray): First input image (RGB or grayscale)
    image2 (np.ndarray): Second input image (RGB or grayscale)
    
    Returns:
    x and y offsets of peak correlation
    """

    ## Convert to grayscale if RGB
    if len(image1.shape) == 3:
        image1 = np.mean(image1, axis=2)
    if len(image2.shape) == 3:
        image2 = np.mean(image2, axis=2)

    ## Get dimensions and pad to next power of 2
    height, width = image1.shape
    next_higher_pwr_2 = lambda n: 2 ** int(np.ceil(np.log2(n)))
    h = next_higher_pwr_2(height)
    w = next_higher_pwr_2(width)
    
    ## Create zero-padded complex array
    data = np.zeros((h, w), dtype=np.complex128)
    
    ## Copy image data, subtracting 128 to center around zero
    data[:height, :width] = image1 - 128
    
    ## Compute FFT of first image
    fft_image1 = fft2(data)
    
    ## Reset data array and do the same for second image
    data = np.zeros((h, w), dtype=np.complex128)
    data[:height, :width] = image2 - 128
    
    ## Compute FFT of second image
    fft_image2 = fft2(data)
    
    ## Cross-correlation in frequency domain
    cross_corr = fft_image1 * np.conj(fft_image2)
    
    ## Inverse FFT to get correlation surface
    correlation_surface = np.real(ifft2(cross_corr))
    
    ## Find peak location
    peak_y, peak_x = np.unravel_index(
        np.argmax(correlation_surface), 
        correlation_surface.shape
    )
    
    ## Adjust for wrap-around
    if peak_x >= w//2:
        peak_x -= w
    if peak_y >= h//2:
        peak_y -= h

    offset = (-peak_x, -peak_y)
    
    return offset

