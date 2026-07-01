#!/usr/bin/env bash
#
# install.sh — self-contained installer for PyReconstruct on Linux (no AppImage).
#
# Creates an isolated Python virtual environment, installs PyReconstruct and its
# pinned dependencies into it, drops a `pyreconstruct` launcher on PATH, and
# registers an application-menu entry with the app icon. Per-user; no root
# required. Re-running performs a clean reinstall/upgrade in place. Remove with
# `install.sh --uninstall` or the companion uninstall.sh.
#
#   bash install.sh [options]
#   bash install.sh --uninstall
#   bash install.sh --help
#
# The same script works from inside a source checkout (it installs that tree) or
# standalone (it installs from a configurable pip source, defaulting to the
# SynapseWeb/PyReconstruct repository).

# Re-exec under bash if started with sh/dash — this script relies on a few bashisms.
if [ -z "${BASH_VERSION:-}" ]; then exec bash "$0" "$@"; fi
set -euo pipefail

INSTALLER_VERSION="1.0.0"

# Default remote source when run outside a checkout and no --source is given.
# No ref is appended, so pip installs the repository's default branch (main).
# Defaults to the latest main for now; will move to the latest tagged stable release (with latest-main kept as an opt-in channel) per the release-strategy proposal.
DEFAULT_SOURCE="git+https://github.com/SynapseWeb/PyReconstruct.git"

# ---- variables the EXIT trap may touch: initialise before `set -u` can bite ----
OWN_LOCK=""      # set to the lock dir once we hold it
OLD_VENV=""      # set to the moved-aside previous venv during a rebuild
VENV=""          # final venv path (set in the paths section)
VENV_OK=0        # 1 once the new venv is built and verified (the commit point)
PATH_RC_EDITED=""

# -------------------------------- helpers ------------------------------------
log()  { printf '==> %s\n' "$*" >&2; }
note() { printf '    %s\n' "$*" >&2; }
warn() { printf 'warning: %s\n' "$*" >&2; }
err()  { printf 'error: %s\n' "$*" >&2; }
die()  { err "$*"; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

usage() {
  cat >&2 <<EOF
PyReconstruct Linux installer ${INSTALLER_VERSION}

Usage:
  install.sh [options]        install or reinstall/upgrade (default)
  install.sh --uninstall      remove a previous install
  install.sh --version        print installer version and exit
  install.sh --help           show this help

Options:
  --python PATH    Python 3.11 interpreter to build the venv with
  --source SPEC    pip source: a git URL, PyPI requirement, local path, or wheel
  --ref REF        git ref (tag/branch/commit) to append to a git source
  --prefix DIR     install root (default: \${XDG_DATA_HOME:-~/.local/share}/PyReconstruct)
  --bin-dir DIR    directory for the launcher (default: \${XDG_BIN_HOME:-~/.local/bin})
  --editable       dev: install a local checkout as an editable install
  --add-to-path    append the launcher dir to your shell rc if it is not on PATH
  --uninstall      run the uninstaller
  -h, --help       show this help

Environment overrides (a flag wins over its variable):
  PYRECON_PYTHON, PYRECON_SOURCE, PYRECON_PREFIX

Examples:
  bash install.sh
  bash install.sh --python /usr/bin/python3.11
  bash install.sh --ref v1.20.0
  bash install.sh --uninstall
EOF
}

# -------------------------------- arguments ----------------------------------
PY_OVERRIDE="${PYRECON_PYTHON:-}"
SRC_OVERRIDE="${PYRECON_SOURCE:-}"
PREFIX_OVERRIDE="${PYRECON_PREFIX:-}"
BIN_OVERRIDE=""
REF=""
EDITABLE=0
ADD_TO_PATH=0
MODE="install"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --python)      PY_OVERRIDE="${2:-}"; shift 2 ;;
    --python=*)    PY_OVERRIDE="${1#*=}"; shift ;;
    --source)      SRC_OVERRIDE="${2:-}"; shift 2 ;;
    --source=*)    SRC_OVERRIDE="${1#*=}"; shift ;;
    --ref)         REF="${2:-}"; shift 2 ;;
    --ref=*)       REF="${1#*=}"; shift ;;
    --prefix)      PREFIX_OVERRIDE="${2:-}"; shift 2 ;;
    --prefix=*)    PREFIX_OVERRIDE="${1#*=}"; shift ;;
    --bin-dir)     BIN_OVERRIDE="${2:-}"; shift 2 ;;
    --bin-dir=*)   BIN_OVERRIDE="${1#*=}"; shift ;;
    --editable)    EDITABLE=1; shift ;;
    --add-to-path) ADD_TO_PATH=1; shift ;;
    --uninstall)   MODE="uninstall"; shift ;;
    --version)     printf 'PyReconstruct Linux installer %s\n' "$INSTALLER_VERSION"; exit 0 ;;
    -h|--help)     usage; exit 0 ;;
    *)             err "unknown option: $1"; usage; exit 2 ;;
  esac
done

# ---------------------------------- paths ------------------------------------
[ -n "${HOME:-}" ] || die "HOME is not set; cannot determine where to install"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
if [ -n "$BIN_OVERRIDE" ]; then BIN_DIR="$BIN_OVERRIDE"; else BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"; fi
if [ -n "$PREFIX_OVERRIDE" ]; then APPROOT="$PREFIX_OVERRIDE"; else APPROOT="$DATA_HOME/PyReconstruct"; fi

# Force absolute paths: a relative --prefix/--bin-dir would bake relative paths
# into the launcher and .desktop (broken when launched from another directory)
# and would make the uninstaller's safety check refuse the install root.
case "$APPROOT" in /*) ;; *) APPROOT="$PWD/$APPROOT" ;; esac
case "$BIN_DIR" in /*) ;; *) BIN_DIR="$PWD/$BIN_DIR" ;; esac

VENV="$APPROOT/venv"
APPS_DIR="$DATA_HOME/applications"
HICOLOR="$DATA_HOME/icons/hicolor"
ICON_DIR="$HICOLOR/512x512/apps"
LAUNCHER="$BIN_DIR/pyreconstruct"
DESKTOP="$APPS_DIR/pyreconstruct.desktop"
ICON="$ICON_DIR/pyreconstruct.png"
MANIFEST="$APPROOT/.install-manifest"
MARKER="$APPROOT/.pyreconstruct-install"
LOCK_DIR="$APPROOT/.install.lock"

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-$0}")" >/dev/null 2>&1 && pwd -P) || SCRIPT_DIR=""

# ------------------------------ uninstall hand-off ---------------------------
if [ "$MODE" = "uninstall" ]; then
  export PYRECON_PREFIX="$APPROOT"   # already canonicalised to an absolute path
  for u in "$APPROOT/uninstall.sh" "$SCRIPT_DIR/uninstall.sh"; do
    if [ -f "$u" ]; then exec bash "$u"; fi
  done
  err "uninstaller not found (looked in $APPROOT and alongside this script)."
  note "Run the standalone uninstaller directly:"
  note "  curl -fsSL https://raw.githubusercontent.com/SynapseWeb/PyReconstruct/main/packaging/linux/uninstall.sh | bash"
  note "or remove $APPROOT and ~/.local/bin/pyreconstruct by hand."
  exit 1
fi

# ------------------------------ python detection -----------------------------
PY=""

py_is_311() {
  # True only for a real CPython 3.11.x with venv+ensurepip. Verify a printed
  # token rather than just the exit status, so a non-Python that ignores -c and
  # exits 0 (e.g. /bin/true) can't be mistaken for an interpreter.
  [ "$("$1" -c 'import sys, platform, venv, ensurepip
print("PYOK" if (sys.version_info[:2] == (3, 11) and platform.python_implementation() == "CPython") else "no")' 2>/dev/null)" = "PYOK" ]
}

no_python_help() {
  cat >&2 <<EOF
error: no usable Python 3.11 found.

PyReconstruct requires CPython 3.11 with the venv module. Install it and retry:
  Debian/Ubuntu:  sudo apt install python3.11 python3.11-venv
  Fedora:         sudo dnf install python3.11
  Other:          https://www.python.org/downloads/  (or pyenv / conda / miniforge)

Or point the installer at an existing 3.11 interpreter:
  bash install.sh --python /path/to/python3.11
  (a conda/miniforge env works too, e.g. ~/miniforge3/envs/<env>/bin/python)
EOF
  exit 1
}

resolve_python() {
  if [ -n "$PY_OVERRIDE" ]; then
    py_is_311 "$PY_OVERRIDE" || die "the chosen Python ($PY_OVERRIDE) is not a usable CPython 3.11 with venv support"
    PY="$PY_OVERRIDE"
  else
    local cand
    for cand in python3.11 python3 python /usr/bin/python3.11 /usr/local/bin/python3.11; do
      if have "$cand" && py_is_311 "$cand"; then PY="$cand"; break; fi
    done
    [ -n "$PY" ] || no_python_help
  fi

  local rl
  rl=$("$PY" -c 'import sys; print(sys.version_info.releaselevel)' 2>/dev/null) || rl="final"
  if [ "$rl" != "final" ]; then
    warn "using a pre-release Python ($("$PY" -c 'import platform; print(platform.python_version())' 2>/dev/null)); a final 3.11 is recommended"
  fi
  PY=$(command -v "$PY" 2>/dev/null) || true
  [ -n "$PY" ] || PY="$PY_OVERRIDE"
}

# ------------------------------ source resolution ----------------------------
SRC=""
SRC_DESC=""

resolve_source() {
  if [ -n "$SRC_OVERRIDE" ]; then
    SRC="$SRC_OVERRIDE"
    case "$SRC" in git+*) [ -n "$REF" ] && SRC="$SRC@$REF" ;; esac
    SRC_DESC="$SRC"
    return
  fi

  # When piped (curl | bash) there is no reliable script dir; go remote.
  local piped=0
  case "${BASH_SOURCE[0]:-}" in ""|bash|sh|-bash|/dev/*|/proc/*) piped=1 ;; esac
  [ -n "$SCRIPT_DIR" ] || piped=1

  if [ "$piped" -eq 0 ]; then
    local d="$SCRIPT_DIR"
    while [ -n "$d" ] && [ "$d" != "/" ]; do
      if [ -f "$d/pyproject.toml" ] && grep -Fq 'name = "pyreconstruct"' "$d/pyproject.toml" 2>/dev/null; then
        SRC="$d"
        if [ "$EDITABLE" -eq 1 ]; then SRC_DESC="$d (local checkout, editable)"; else SRC_DESC="$d (local checkout)"; fi
        return
      fi
      d=$(dirname -- "$d")
    done
  fi

  SRC="$DEFAULT_SOURCE"
  [ -n "$REF" ] && SRC="$SRC@$REF"
  SRC_DESC="$SRC (default)"
}

# --------------------------------- preflight ---------------------------------
preflight() {
  mkdir -p "$APPROOT" "$BIN_DIR" "$APPS_DIR" "$ICON_DIR" 2>/dev/null || true
  local d
  for d in "$APPROOT" "$BIN_DIR" "$APPS_DIR" "$ICON_DIR"; do
    { [ -d "$d" ] && [ -w "$d" ]; } || die "cannot write to $d — check permissions, or use --prefix / --bin-dir"
  done
  case "$SRC" in
    git+*) have git || die "git is required to install from a git source — install git (e.g. sudo apt install git) and retry" ;;
  esac
  local arch; arch=$(uname -m 2>/dev/null) || arch="unknown"
  case "$arch" in
    x86_64|amd64) : ;;
    *) warn "architecture is '$arch'; PyReconstruct's pinned wheels (PySide6, vtk, numpy, opencv) target x86_64 and may be unavailable here — the install may fail or build slowly from source" ;;
  esac
}

# --------------------------------- locking -----------------------------------
acquire_lock() {
  if mkdir "$LOCK_DIR" 2>/dev/null; then
    OWN_LOCK="$LOCK_DIR"
  else
    die "another PyReconstruct install appears to be running (lock: $LOCK_DIR). If not, remove it and retry."
  fi
}

cleanup() {
  # Roll back only if the new venv never reached the commit point.
  if [ "$VENV_OK" != 1 ]; then
    [ -n "$VENV" ] && [ -d "$VENV" ] && rm -rf -- "$VENV" 2>/dev/null || true
    # Restore the previous venv only if the partial new one is truly gone, so a
    # failed rm above can't cause the old venv to be nested inside a broken dir.
    if [ -n "$OLD_VENV" ] && [ -d "$OLD_VENV" ]; then
      if [ ! -e "$VENV" ] && mv -- "$OLD_VENV" "$VENV" 2>/dev/null; then
        warn "install did not complete; restored the previous PyReconstruct install"
      else
        warn "install did not complete; previous install preserved at $OLD_VENV"
      fi
    fi
  fi
  [ -n "$OWN_LOCK" ] && rmdir -- "$OWN_LOCK" 2>/dev/null || true
}

# ------------------------------- venv build ----------------------------------
build_venv() {
  # Reclaim any orphaned previous-venv copies left by a prior hard kill
  # (SIGKILL/power loss between move-aside and commit, when the trap can't run).
  local o
  for o in "$APPROOT"/.venv-old.*; do [ -e "$o" ] && rm -rf -- "$o" || true; done

  # A venv cannot be relocated after creation (its script shebangs bake in the
  # absolute path), so we build at the final path. To keep a working install
  # safe across a failed reinstall, move any existing venv aside first and let
  # the EXIT trap restore it if we don't finish.
  if [ -d "$VENV" ]; then
    OLD_VENV="$APPROOT/.venv-old.$$"
    rm -rf -- "$OLD_VENV"
    mv -- "$VENV" "$OLD_VENV"
  fi

  log "Creating virtual environment ($("$PY" -c 'import platform;print("Python "+platform.python_version())' 2>/dev/null || echo Python))"
  "$PY" -m venv "$VENV" || die "failed to create the virtual environment with $PY"

  if ! "$VENV/bin/python" -m pip --version >/dev/null 2>&1; then
    "$VENV/bin/python" -m ensurepip --upgrade >/dev/null 2>&1 || true
  fi
  "$VENV/bin/python" -m pip --version >/dev/null 2>&1 \
    || die "the new virtual environment has no pip — install the python3.11-venv package and retry"

  log "Upgrading pip and wheel"
  "$VENV/bin/python" -m pip install --upgrade pip wheel >/dev/null

  log "Installing PyReconstruct from: $SRC_DESC"
  note "(first run downloads several hundred MB of scientific/Qt wheels)"
  local -a pip_src
  if [ "$EDITABLE" -eq 1 ]; then pip_src=(-e "$SRC"); else pip_src=("$SRC"); fi
  if ! "$VENV/bin/python" -m pip install --upgrade --upgrade-strategy only-if-needed "${pip_src[@]}"; then
    err "pip failed to install PyReconstruct."
    note "- if you are offline, reconnect and re-run"
    local arch; arch=$(uname -m 2>/dev/null) || arch="unknown"
    case "$arch" in x86_64|amd64) : ;; *) note "- on '$arch' some pinned wheels are unavailable; a source build may be needed (or use conda)";; esac
    exit 1
  fi
}

# --------------------------------- verify ------------------------------------
APP_VER=""
smoke_test() {
  log "Verifying the installation"
  # -P keeps the cwd off sys.path, so this resolves the *installed* package even
  # when the installer is run from inside the source checkout.
  "$VENV/bin/python" -P -c 'import PyReconstruct, PySide6, vtk' \
    || die "post-install import check failed (PyReconstruct / PySide6 / vtk did not import)"
  APP_VER=$("$VENV/bin/python" -P -c 'import importlib.metadata as m; print(m.version("PyReconstruct"))' 2>/dev/null) || APP_VER="unknown"
  if ! QT_QPA_PLATFORM=offscreen "$VENV/bin/python" -P -c 'import PyReconstruct.modules.gui.main' >/dev/null 2>&1; then
    warn "GUI module did not import under offscreen Qt (often fine on a headless box; check on a desktop)"
  fi
}

# ------------------------------- launcher ------------------------------------
write_launcher() {
  log "Installing launcher: $LAUNCHER"
  mkdir -p "$BIN_DIR"
  # Refuse a non-regular-file target (e.g. a leftover directory) so `mv -f` can't
  # move the launcher *into* it and silently break the command on PATH.
  if [ -e "$LAUNCHER" ] && [ ! -f "$LAUNCHER" ] && [ ! -L "$LAUNCHER" ]; then
    die "$LAUNCHER exists and is not a regular file; remove it and retry"
  fi
  local tmp; tmp=$(mktemp "$BIN_DIR/.pyreconstruct.XXXXXX")
  # $VENV is expanded now; runtime variables are escaped to stay literal.
  if ! cat >"$tmp" <<EOF
#!/bin/sh
# PyReconstruct launcher — generated by packaging/linux/install.sh. Do not edit;
# re-run the installer to regenerate.
VENV_BIN="$VENV/bin"
if [ "\$#" -eq 0 ]; then
  exec "\$VENV_BIN/PyReconstruct"
elif [ "\$#" -eq 1 ] && [ "\${1#-}" = "\$1" ]; then
  # a single non-flag argument (a file path, incl. file-manager Exec %f) maps to -f
  exec "\$VENV_BIN/PyReconstruct" -f "\$1"
else
  exec "\$VENV_BIN/PyReconstruct" "\$@"
fi
EOF
  then rm -f -- "$tmp"; die "failed to write the launcher"; fi
  chmod 0755 "$tmp"
  mv -f "$tmp" "$LAUNCHER"
}

# --------------------------------- icon --------------------------------------
install_icon() {
  local src
  src=$("$VENV/bin/python" -P -c 'import PyReconstruct, os; print(os.path.join(os.path.dirname(PyReconstruct.__file__), "assets", "img", "logo.png"))' 2>/dev/null) || src=""
  if [ -n "$src" ] && [ -f "$src" ]; then
    log "Installing icon: $ICON"
    mkdir -p "$ICON_DIR"
    install -m 0644 "$src" "$ICON"
    install -m 0644 "$src" "$APPROOT/icon.png"
  else
    warn "could not locate the app icon in the installed package; the menu entry will use a generic icon"
    ICON=""
  fi
}

# ------------------------------- desktop entry -------------------------------
install_desktop() {
  log "Installing menu entry: $DESKTOP"
  mkdir -p "$APPS_DIR"
  local tmpl="$SCRIPT_DIR/pyreconstruct.desktop.in"
  local tmp; tmp=$(mktemp "$APPS_DIR/.pyreconstruct.XXXXXX")
  if [ -n "$SCRIPT_DIR" ] && [ -f "$tmpl" ]; then
    # bash parameter expansion is metachar-safe; `sed s|@EXEC@|$LAUNCHER|` would
    # break on a launcher path containing & | or \.
    local line
    if ! { while IFS= read -r line || [ -n "$line" ]; do printf '%s\n' "${line//@EXEC@/$LAUNCHER}"; done <"$tmpl"; } >"$tmp"; then
      rm -f -- "$tmp"; die "failed to render the desktop entry"
    fi
  else
    if ! cat >"$tmp" <<EOF
[Desktop Entry]
Type=Application
Version=1.4
Name=PyReconstruct
GenericName=Image Reconstruction Tool
Comment=RECONSTRUCT in Python
Exec="$LAUNCHER" %f
TryExec=$LAUNCHER
Icon=pyreconstruct
Terminal=false
Categories=Science;Biology;
Keywords=reconstruct;neuron;segmentation;microscopy;electron;
StartupNotify=true
StartupWMClass=PyReconstruct
EOF
    then rm -f -- "$tmp"; die "failed to write the desktop entry"; fi
  fi
  chmod 0644 "$tmp"
  mv -f "$tmp" "$DESKTOP"
  if have desktop-file-validate; then
    desktop-file-validate "$DESKTOP" || warn "desktop-file-validate reported issues (non-fatal)"
  fi
}

refresh_caches() {
  have update-desktop-database && update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
  have gtk-update-icon-cache && gtk-update-icon-cache -f -t "$HICOLOR" >/dev/null 2>&1 || true
}

# ------------------------------- PATH handling -------------------------------
PATH_OK=0
add_path_block() {
  local rc="$1"
  mkdir -p "$(dirname -- "$rc")" 2>/dev/null || true
  if [ -f "$rc" ] && grep -Fq '# >>> PyReconstruct >>>' "$rc"; then PATH_RC_EDITED="$rc"; return; fi
  {
    printf '\n# >>> PyReconstruct >>>\n'
    # $PATH must stay literal here — it is expanded later by the user's shell.
    # shellcheck disable=SC2016
    printf 'export PATH="%s:$PATH"\n' "$BIN_DIR"
    printf '# <<< PyReconstruct <<<\n'
  } >>"$rc"
  PATH_RC_EDITED="$rc"
  note "added $BIN_DIR to PATH in $rc (open a new shell to pick it up)"
}

# If an earlier run left our PATH block in a shell rc, remember it so the manifest
# keeps recording it (even on a reinstall without --add-to-path) and uninstall can
# still remove it.
detect_existing_path_block() {
  local rc
  for rc in "$HOME/.bashrc" "${ZDOTDIR:-$HOME}/.zshrc"; do
    if [ -f "$rc" ] && grep -Fq '# >>> PyReconstruct >>>' "$rc"; then PATH_RC_EDITED="$rc"; return; fi
  done
}

path_advice() {
  detect_existing_path_block
  case ":$PATH:" in *":$BIN_DIR:"*) PATH_OK=1 ;; *) PATH_OK=0 ;; esac
  [ "$PATH_OK" -eq 1 ] && return 0
  if [ "$ADD_TO_PATH" -eq 1 ]; then
    case "$(basename -- "${SHELL:-}")" in
      bash) add_path_block "$HOME/.bashrc" ;;
      zsh)  add_path_block "${ZDOTDIR:-$HOME}/.zshrc" ;;
      *)    warn "--add-to-path supports bash/zsh only; add $BIN_DIR to your shell rc by hand" ;;
    esac
  fi
  return 0
}

# -------------------------------- manifest -----------------------------------
write_manifest() {
  printf '%s\n' "$APPROOT" >"$MARKER"
  {
    printf '# PyReconstruct installer manifest v1\n'
    printf 'prefix %s\n' "$APPROOT"
    printf '%s\n' "$LAUNCHER"
    printf '%s\n' "$DESKTOP"
    if [ -n "$ICON" ]; then printf '%s\n' "$ICON"; fi
    if [ -n "$PATH_RC_EDITED" ]; then printf 'pathrc %s\n' "$PATH_RC_EDITED"; fi
  } >"$MANIFEST"
  if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/uninstall.sh" ]; then
    install -m 0755 "$SCRIPT_DIR/uninstall.sh" "$APPROOT/uninstall.sh"
  fi
}

# --------------------------------- summary -----------------------------------
print_summary() {
  printf '\n' >&2
  log "PyReconstruct ${APP_VER} installed."
  note "Location:   $APPROOT"
  note "Launcher:   $LAUNCHER"
  note "Menu entry: $DESKTOP"
  printf '\n' >&2
  if [ "$PATH_OK" -eq 1 ]; then
    note "Start it from a terminal:  pyreconstruct"
  else
    note "The application-menu entry works now (it uses an absolute path)."
    note "To run 'pyreconstruct' in a terminal, put $BIN_DIR on your PATH:"
    case "$(basename -- "${SHELL:-sh}")" in
      fish) note "    fish_add_path $BIN_DIR" ;;
      *)    note "    echo 'export PATH=\"$BIN_DIR:\$PATH\"' >> ~/.bashrc   # or your shell's rc"
            note "    then open a new shell" ;;
    esac
    note "Or run it directly:        $LAUNCHER"
  fi
  printf '\n' >&2
  note "Upgrade:    re-run this installer."
  note "Uninstall:  bash \"$APPROOT/uninstall.sh\"   (or: install.sh --uninstall)"
  note "The app's own 'update' / 'switch branch' actions are not used for this"
  note "isolated install — upgrade by re-running the installer."
}

# ---------------------------------- main -------------------------------------
resolve_python
resolve_source
preflight
acquire_lock
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

build_venv
smoke_test
# Commit point: the new venv is built and verified. Mark it good *before* deleting
# the moved-aside old venv, so an interrupt during that rm can't make the trap
# discard the verified new venv.
VENV_OK=1
if [ -n "$OLD_VENV" ]; then rm -rf -- "$OLD_VENV" 2>/dev/null || true; OLD_VENV=""; fi

write_launcher
install_icon
install_desktop
refresh_caches
# path_advice must run before write_manifest: it may record a shell-rc PATH edit
# (PATH_RC_EDITED) that the manifest needs so uninstall can undo it.
path_advice
write_manifest
print_summary
