#!/usr/bin/env python

"""View zarrs in neuroglancer.

Example call: python -i ./ng_view.py <path to zarr>
"""

import neuroglancer
import numpy as np
import os
import sys
import webbrowser
import zarr

print(sys.argv[1])

neuroglancer.set_server_bind_address('localhost', bind_port=3334)

f = zarr.open(sys.argv[1])

datasets = [i for i in os.listdir(sys.argv[1]) if '.' not in i]

res = f[datasets[0]].attrs['resolution']

viewer = neuroglancer.Viewer()

dims = neuroglancer.CoordinateSpace(
        names=['c^','z','y','x'],
        units='nm',
        scales=[1,]+res)

with viewer.txn() as s:

    for ds in datasets:

        offset = f[ds].attrs['offset']

        offset = [0,] + [int(i/j) for i,j in zip(offset, res)]

        data = f[ds]

        if ds == "raw":
            data = np.expand_dims(data, axis=0)

        shader="""
void main() {
    emitRGB(
        vec3(
            toNormalized(getDataValue(0)),
            toNormalized(getDataValue(1)),
            toNormalized(getDataValue(2)))
        );
}"""

        try:
            
            if 'label' not in ds and 'seg' not in ds:
                s.layers[ds] = neuroglancer.ImageLayer(
                    source=neuroglancer.LocalVolume(
                        data=data,
                        voxel_offset=offset,
                        dimensions=dims),
                    shader=shader)
            else:
                s.layers[ds] = neuroglancer.SegmentationLayer(
                    source=neuroglancer.LocalVolume(
                        data=data,#np.expand_dims(data,axis=1),
                        voxel_offset=offset,
                        dimensions=dims))

        except Exception as e:
            print(ds, e)

    s.layout = 'yz' 

print(viewer)
