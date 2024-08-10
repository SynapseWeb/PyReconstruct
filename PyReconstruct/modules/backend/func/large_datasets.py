import numpy as np


def scale_block(in_array, out_array, factor, mode, block) -> bool:
    """Scale a single block."""

    from daisy import Coordinate
    from funlib.persistence import Array
    from skimage.measure import block_reduce
    from skimage.transform import rescale
    
    dims = len(factor)
    in_data = in_array.to_ndarray(block.read_roi, fill_value=0)
    name = in_array.data.name

    in_shape = Coordinate(in_data.shape[-dims:])
    
    n_channels = len(in_data.shape) - dims
    if n_channels >= 1:
        factor = (1,)*n_channels + factor

    if in_data.dtype == np.uint64 or 'label' in name or 'id' in name:
        
        if mode == 'down':
            slices = tuple(slice(k//2, None, k) for k in factor)
            out_data = in_data[slices]
            
        else:  # upscale
            out_data = in_data
            for axis, f in enumerate(factor):
                out_data = np.repeat(out_data, f, axis=axis)
    else:
        
        if mode == 'down':
            out_data = block_reduce(in_data, factor, np.mean)
            
        else:  # upscale
            out_data = rescale(in_data, factor, order=1, preserve_range=True)

    try:
        
        out_data_array = Array(out_data,block.read_roi,out_array.voxel_size)
        out_array[block.write_roi] = out_data_array.to_ndarray(block.write_roi)
        
    except Exception:
        
        print("Failed to write to %s" % block.write_roi)
        raise

    return True



def scale_array():
    """Scale an array blockwise."""
    
    pass
