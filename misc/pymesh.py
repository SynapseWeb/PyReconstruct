import pymeshlab
import numpy as np

verts = np.array([
    [-0.5, -0.5, -0.5],
    [0.5, -0.5, -0.5],
    [-0.5, 0.5, -0.5],
    [0.5, 0.5, -0.5],
    [-0.5, -0.5, 0.5],
    [0.5, -0.5, 0.5],
    [-0.5, 0.5, 0.5],
    [0.5, 0.5, 0.5]])

m = pymeshlab.Mesh(verts)

# create a new MeshSet
ms = pymeshlab.MeshSet()

# add the mesh to the
ms.add_mesh(m, "cube_mesh")

ms.apply_filter('generate_voronoi_filtering')
ms.apply_filter('generate_voronoi_scaffolding')
ms.apply_filter('meshing_repair_non_manifold_vertices')

# save the current
ms.save_current_mesh("/tmp/pymesh/saved_cube_from_array.ply")
ms.save_current_mesh('/tmp/pymesh/example.obj')

pymeshlab.print_filter_list()
