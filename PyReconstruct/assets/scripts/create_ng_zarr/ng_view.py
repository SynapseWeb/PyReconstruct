#!/usr/bin/env python

"""View zarrs in neuroglancer.

Example call: python -i ./ng_view.py <path to zarr>
"""

import sys
import zarr
import neuroglancer

## Open zarr

f = zarr.open(sys.argv[1])

## Create viewer

ip = 'localhost'
port = 9999

neuroglancer.set_server_bind_address(bind_address=ip, bind_port=port)

viewer = neuroglancer.Viewer()

## Get resolution

resolution = f['raw'].attrs.get("resolution")

res = neuroglancer.CoordinateSpace(names = ['z', 'y', 'x'],
                                   units = ['nm', 'nm', 'nm'],
                                   scales = resolution)

## Add layers

def ngLayer(data, res, oo=[0,0,0], tt='segmentation'):
	return neuroglancer.LocalVolume(data, dimensions=res, volume_type=tt, voxel_offset=oo)

zarr_subdirs = [elem for elem in list(f.keys()) if elem != 'raw']
layers = ['raw'] + zarr_subdirs  # place 'raw' before labels

with viewer.txn() as s:

    for layer in layers:

        layer_data = f[layer][:]
        layer_name = layer.replace('labels_', '')
        layer_vol_type = 'image' if layer_name == 'raw' else 'segmentation'
    
        s.layers.append(name=layer_name, layer=ngLayer(layer_data, res, tt=layer_vol_type))

## Initialize viewer (make sure to call python interactively [-i])

print(viewer)
