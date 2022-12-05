"""
.. _surface_reconstruction_example:

Surface Reconstruction
~~~~~~~~~~~~~~~~~~~~~~

Surface reconstruction has a dedicated filter in PyVista and is
handled by :func:`pyvista.PolyDataFilters.reconstruct_surface`.  This
tends to perform much better than :func:`DataSetFilters.delaunay_3d`.

"""
import pyvista as pv
import numpy as np
from pyvista.core.pointset import PolyData, UnstructuredGrid
from modules.pyrecon.series import Series

series = Series(r"C:\Users\jfalco\Documents\Series\DSNYJ_JSON\DSNYJ.ser")

obj_name = "d001"

points = []
z = 0
for snum in range(78, 278):
    section = series.loadSection(snum)
    tform = section.tforms[series.alignment]
    if obj_name in section.contours:
        for trace in section.contours[obj_name]:
            for pt in trace.points:
                x, y = tform.map(*pt)
                points.append((x, y, z))
    z += section.thickness


###############################################################################
# Create a point cloud from a sphere and then reconstruct a surface from it.

pdata = PolyData(np.array(points))
surf = pdata.delaunay_3d(alpha=0.1)
surf : UnstructuredGrid
new_pdata = surf.extract_surface()

###############################################################################
# Plot the point cloud and the reconstructed sphere.

pl = pv.Plotter(shape=(1, 2))
pl.add_mesh(pdata)
pl.add_title('Point Cloud of 3D Surface')
pl.subplot(0, 1)
pl.add_mesh(new_pdata, color=True, show_edges=False)
pl.add_title('Reconstructed Surface')
pl.show()
