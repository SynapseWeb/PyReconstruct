"""Helpers for detecting and adapting to a frozen (PyInstaller) bundle.

Kept dependency-free (stdlib only) so it can be imported very early by other
``constants`` modules such as ``locations`` and ``repo_info`` without risking
import cycles.
"""

import os
import sys
from pathlib import Path


def is_frozen() -> bool:
    """Return True when running inside a frozen bundle (e.g. PyInstaller).

    Setting ``PYRECON_FORCE_FROZEN=1`` forces this on, so the frozen code paths
    can be exercised from a source checkout for testing.
    """
    if os.environ.get("PYRECON_FORCE_FROZEN") == "1":
        return True
    return bool(getattr(sys, "frozen", False))


def bundle_base() -> Path:
    """Root directory of the bundled files when frozen.

    PyInstaller unpacks/collects data under ``sys._MEIPASS``. When running from
    source (or when forced frozen for testing), fall back to the repository root
    so that ``bundle_base() / "PyReconstruct"`` resolves to the package dir.
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    # .../PyReconstruct/modules/constants/frozen.py -> repo root is parents[3]
    return Path(__file__).resolve().parents[3]


def script_launch_prefix():
    """argv prefix for relaunching a bundled python script with this runtime.

    Source build: ``[sys.executable]`` (a real Python runs the .py directly).
    Frozen build: ``[sys.executable, "__run_script__"]`` -- the frozen exe has
    no Python CLI, so ``run.py``'s ``__main__`` intercepts this sentinel and
    runs the given script via ``runpy``. The caller appends the script path and
    its args.

    Uses the real ``sys.frozen`` (not the PYRECON_FORCE_FROZEN test override),
    since this governs how a real subprocess is actually spawned.
    """
    if bool(getattr(sys, "frozen", False)):
        return [sys.executable, "__run_script__"]
    return [sys.executable]
