# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for PyReconstruct (one-folder build).

Run from the repository root, after installing the project + PyInstaller into a
Python 3.11 environment (`pip install -e .` writes PyReconstruct/_version.py):

    pyinstaller --noconfirm packaging/PyReconstruct.spec

Output:
    Windows : dist/PyReconstruct/PyReconstruct.exe
    macOS   : dist/PyReconstruct.app   (needs packaging/PyReconstruct.icns first)

NOTE on VTK: vtk is pinned to 9.3.1 (the version the app's 3D viewer is written
against), which pyinstaller-hooks-contrib covers. The explicit hiddenimports
below are kept as belt-and-suspenders to guarantee the OpenGL render stack is
bundled. If the 3D viewport ever renders blank in a frozen build, the fallback
is to build that platform via conda constructor.
"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

# SPECPATH is the absolute path of the directory containing this spec (packaging/).
REPO_ROOT = Path(SPECPATH).parent
PKG_DIR = REPO_ROOT / "PyReconstruct"
ASSETS = PKG_DIR / "assets"
ENTRY = str(PKG_DIR / "run.py")

datas = []
binaries = []
hiddenimports = []

# --- App assets: welcome series, icons, the "checker" data, and the helper .py
#     scripts that run.py relaunches via runpy. Bundle the full tree at
#     <_MEIPASS>/PyReconstruct/assets so locations.py (frozen branch) finds it.
for _p in ASSETS.rglob("*"):
    if _p.is_file():
        _dest = Path("PyReconstruct/assets") / _p.relative_to(ASSETS).parent
        datas.append((str(_p), str(_dest)))

# --- setuptools-scm version file (frozen repo_info reads PyReconstruct._version)
_version_file = PKG_DIR / "_version.py"
if _version_file.exists():
    datas.append((str(_version_file), "PyReconstruct"))

# --- VTK: hooks-contrib covers it; we still collect everything and force the
#     render/interaction modules as belt-and-suspenders vs a blank viewport.
_vd, _vb, _vh = collect_all("vtkmodules")
datas += _vd
binaries += _vb
hiddenimports += _vh
hiddenimports += [
    "vtkmodules.vtkRenderingOpenGL2",         # <- the key one (GL2 render factory)
    "vtkmodules.vtkRenderingFreeType",
    "vtkmodules.vtkRenderingUI",
    "vtkmodules.vtkRenderingVolumeOpenGL2",
    "vtkmodules.vtkRenderingContextOpenGL2",
    "vtkmodules.vtkRenderingAnnotation",
    "vtkmodules.vtkInteractionStyle",
    "vtkmodules.vtkInteractionWidgets",
    "vtkmodules.vtkRenderingCore",
    "vtkmodules.vtkCommonCore",
    "vtkmodules.vtkCommonDataModel",
    "vtkmodules.vtkCommonExecutionModel",
    "vtkmodules.vtkCommonMath",
    "vtkmodules.vtkCommonTransforms",
    "vtkmodules.vtkFiltersCore",
    "vtkmodules.vtkFiltersGeneral",
    "vtkmodules.vtkFiltersSources",
    "vtkmodules.vtkFiltersModeling",
    "vtkmodules.vtkIOImage",
    "vtkmodules.vtkIOXML",
    "vtkmodules.vtkIOGeometry",
    "vtkmodules.util.numpy_support",
    "vtkmodules.util.execution_model",
    "vtkmodules.qt",
    "vtkmodules.qt.QVTKRenderWindowInteractor",
    "vtk",
]

# --- vedo data (fonts, textures, colormaps) ---
datas += collect_data_files("vedo")

# --- scipy / scikit-image: lazily-imported submodules + data files ---
hiddenimports += collect_submodules("scipy")
hiddenimports += collect_submodules("skimage")
datas += collect_data_files("skimage")

# --- cloud-volume and its compiled codecs (best-effort; import names vary and
#     not all expose data/hooks). Failures here only affect remote-volume use.
for _pkg in (
    "cloudvolume", "DracoPy", "compressed_segmentation", "fpzip",
    "compresso", "crackle", "zfpc", "numcodecs", "zarr", "fastremap",
):
    try:
        _d, _b, _h = collect_all(_pkg)
        datas += _d
        binaries += _b
        hiddenimports += _h
    except Exception:
        pass

# --- trimesh data ---
datas += collect_data_files("trimesh")

# --- certifi CA bundle: a frozen app has no OS trust store, so urllib/ssl can't
#     verify TLS certificates (cloud-volume over HTTPS, git operations over TLS).
#     Bundle certifi's cacert.pem; rthook_ssl.py points SSL_CERT_FILE at it at launch.
hiddenimports += ["certifi"]
datas += collect_data_files("certifi")

# --- Software OpenGL fallback (Windows): VTK 9's renderer needs OpenGL >= 3.2.
#     Over RDP or in a GPU-less VM the system opengl32.dll exposes only OpenGL
#     1.1, so VTK calls a null GL function pointer when the 3D viewport opens and
#     the whole app crashes (access violation at offset 0, "unknown" module).
#     Bundle Qt's software GL (Mesa llvmpipe, shipped with PySide6 as
#     opengl32sw.dll) renamed to mesa/opengl32.dll. rthook_gl.py preloads it ONLY
#     when hardware GL is inadequate (RDP session, or PYRECON_SOFTWARE_GL set), so
#     GPU machines keep fast hardware rendering.
if sys.platform.startswith("win"):
    import glob as _glob, shutil as _shutil, PySide6 as _ps6mod
    _ps6 = Path(_ps6mod.__file__).parent
    _sw = _glob.glob(str(_ps6 / "**" / "opengl32sw.dll"), recursive=True)
    if _sw:
        _mesa_dir = REPO_ROOT / "build" / "mesa_gl"
        _mesa_dir.mkdir(parents=True, exist_ok=True)
        _dst = _mesa_dir / "opengl32.dll"
        _shutil.copy(_sw[0], str(_dst))
        binaries += [(str(_dst), "mesa")]
        print(f"[spec] software-GL fallback: bundling {_sw[0]} -> mesa/opengl32.dll")
    else:
        print("[spec] WARNING: opengl32sw.dll not found under PySide6; no software-GL fallback bundled")

block_cipher = None

a = Analysis(
    [ENTRY],
    pathex=[str(REPO_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[
        str(REPO_ROOT / "packaging" / "rthook_stdio.py"),  # must run first
        str(REPO_ROOT / "packaging" / "rthook_qt.py"),
        str(REPO_ROOT / "packaging" / "rthook_ssl.py"),
        str(REPO_ROOT / "packaging" / "rthook_gl.py"),
    ],
    excludes=[
        "PyQt5", "PyQt6", "PySide2",   # forbid clashing Qt bindings
        "tkinter",
        "matplotlib.tests",
        "cv2.qt",                       # belt-and-suspenders (we ship cv2 headless)
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

is_win = sys.platform.startswith("win")
is_mac = sys.platform == "darwin"

win_icon = str(PKG_DIR / "assets" / "img" / "PyReconstruct.ico")
mac_icon = str(REPO_ROOT / "packaging" / "PyReconstruct.icns")  # built by make_icns.sh
if not Path(mac_icon).exists():   # allow a local build that skipped make_icns.sh
    mac_icon = None

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PyReconstruct",
    console=False,            # windowed (no console window)
    icon=win_icon if is_win else (mac_icon if is_mac else None),
    upx=False,                # UPX corrupts Qt/VTK shared libraries
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="PyReconstruct",
    upx=False,
)

if is_mac:
    app = BUNDLE(
        coll,
        name="PyReconstruct.app",
        icon=mac_icon,
        bundle_identifier="edu.utexas.synapseweb.pyreconstruct",
        info_plist={"NSHighResolutionCapable": True},
    )
