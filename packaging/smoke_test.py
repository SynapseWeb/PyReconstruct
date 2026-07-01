"""Headless smoke test for CI / local checks.

Builds a QApplication, imports the app's GUI + 3D-viewport modules (catches a
freeze that's missing modules), and renders a VTK scene offscreen.

    QT_QPA_PLATFORM=offscreen python packaging/smoke_test.py

The offscreen VTK render needs a real OpenGL context. macOS runners and any
machine with a display have one; headless CI (esp. Windows runners / bare Linux)
may not, and VTK can *segfault* rather than raise without one. So set
PYRECON_SMOKE_SKIP_RENDER=1 in CI to run the import checks only — the definitive
"does the 3D viewport actually render" check is a manual launch on a real
machine (the Windows VM).
"""

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv)

# Importing this registers the OpenGL2 render factory; a freeze missing the
# vtkRendering* modules fails here (the cheap, reliable freeze-break catcher).
import vtkmodules.vtkRenderingOpenGL2  # noqa: F401
import vtk

# Import the app's GUI package and the 3D-viewport module (the render-risk path).
import PyReconstruct.modules.gui.main  # noqa: F401
import PyReconstruct.modules.gui.popup.custom_plotter  # noqa: F401

from PyReconstruct.modules.constants import repo_string

if os.environ.get("PYRECON_SMOKE_SKIP_RENDER"):
    print(f"smoke OK (imports only, render skipped): {repo_string}")
    sys.exit(0)

# Actual offscreen render — proves the OpenGL2 backend works (not just imports).
render_window = vtk.vtkRenderWindow()
render_window.SetOffScreenRendering(1)
renderer = vtk.vtkRenderer()
render_window.AddRenderer(renderer)

mapper = vtk.vtkPolyDataMapper()
mapper.SetInputConnection(vtk.vtkSphereSource().GetOutputPort())
actor = vtk.vtkActor()
actor.SetMapper(mapper)
renderer.AddActor(actor)
render_window.Render()

grab = vtk.vtkWindowToImageFilter()
grab.SetInput(render_window)
grab.Update()
dims = grab.GetOutput().GetDimensions()
assert dims[0] > 0 and dims[1] > 0, f"VTK produced no image (dims={dims})"

print(f"smoke OK: {repo_string} | VTK offscreen image {dims}")
