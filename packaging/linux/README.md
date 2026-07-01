# PyReconstruct on Linux (`.sh` installer)

A self-contained shell installer — **no AppImage, no root**. It builds an
isolated virtual environment, installs PyReconstruct and its pinned
dependencies into it, drops a `pyreconstruct` launcher on your PATH, and adds an
application-menu entry with the app icon.

| File | Purpose |
|------|---------|
| `install.sh` | the installer (build venv, launcher, menu entry, icon) |
| `uninstall.sh` | safe uninstaller (also copied into the install root) |
| `pyreconstruct.desktop.in` | desktop-entry template (`@EXEC@` → launcher path) |

## Install

From a source checkout (installs that tree):

```bash
bash packaging/linux/install.sh
```

Standalone — the same script installs from the fork when run outside a checkout:

```bash
curl -fsSL https://raw.githubusercontent.com/SynapseWeb/PyReconstruct/main/packaging/linux/install.sh | bash
```

Then launch it from your application menu, or run `pyreconstruct`. If
`~/.local/bin` is not on your PATH, the installer prints the one line to add it
(or pass `--add-to-path`).

### Requirements

- **CPython 3.11** with `venv` (Debian/Ubuntu: `sudo apt install python3.11 python3.11-venv`).
  The installer finds `python3.11` automatically; override with `--python /path/to/python3.11`
  (a conda/miniforge 3.11 works) or `PYRECON_PYTHON`.
- Internet access for the first install (it downloads several hundred MB of wheels).
- x86_64 (the pinned PySide6/vtk/numpy wheels target it).

## Options

```
--python PATH    Python 3.11 interpreter to build the venv with
--source SPEC    pip source: git URL, PyPI requirement, local path, or wheel
--ref REF        git ref (tag/branch/commit) appended to a git source
--prefix DIR     install root (default: $XDG_DATA_HOME/PyReconstruct)
--bin-dir DIR    launcher directory (default: $XDG_BIN_HOME or ~/.local/bin)
--editable       dev: editable install of a local checkout
--add-to-path    append the launcher dir to your shell rc if missing from PATH
--uninstall      remove a previous install
```

Re-running the installer performs a clean reinstall/upgrade in place. A failed
reinstall is rolled back to the previous working version.

## What it installs

```
$XDG_DATA_HOME/PyReconstruct/venv            isolated environment
$XDG_DATA_HOME/PyReconstruct/uninstall.sh    self-contained uninstaller
~/.local/bin/pyreconstruct                   launcher
$XDG_DATA_HOME/applications/pyreconstruct.desktop
$XDG_DATA_HOME/icons/hicolor/512x512/apps/pyreconstruct.png
```

## Uninstall

```bash
bash packaging/linux/install.sh --uninstall
# or, without the checkout:
bash ~/.local/share/PyReconstruct/uninstall.sh
# or, if you installed via curl and kept nothing locally:
curl -fsSL https://raw.githubusercontent.com/SynapseWeb/PyReconstruct/main/packaging/linux/uninstall.sh | bash
```

The uninstaller removes only what the installer added (venv, launcher, menu
entry, icon). Your `.jser` series files and config are never touched.

## Notes

- Updating: re-run `install.sh`. The app's in-app *update* / *switch branch*
  actions assume a plain `pip` install and are not used for this isolated venv.
- This installs from source (it is not a frozen bundle), so it relies on a
  system Python 3.11 being present; the venv keeps its dependencies isolated.
