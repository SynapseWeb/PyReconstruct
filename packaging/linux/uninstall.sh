#!/usr/bin/env bash
#
# uninstall.sh — remove a PyReconstruct install created by install.sh.
#
# Removes only what the installer added: the venv/install root, the launcher,
# the menu entry, and the icon. User data (.jser series files and config) is
# never touched. A copy of this script is placed in the install root so it can
# be run without the source checkout.
#
#   bash uninstall.sh [--prefix DIR]

if [ -z "${BASH_VERSION:-}" ]; then exec bash "$0" "$@"; fi
set -euo pipefail

log()  { printf '==> %s\n' "$*" >&2; }
note() { printf '    %s\n' "$*" >&2; }
warn() { printf 'warning: %s\n' "$*" >&2; }
err()  { printf 'error: %s\n' "$*" >&2; }
die()  { err "$*"; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

PREFIX_OVERRIDE="${PYRECON_PREFIX:-}"
while [ "$#" -gt 0 ]; do
  case "$1" in
    --prefix)   PREFIX_OVERRIDE="${2:-}"; shift 2 ;;
    --prefix=*) PREFIX_OVERRIDE="${1#*=}"; shift ;;
    -h|--help)  printf 'Usage: uninstall.sh [--prefix DIR]\n' >&2; exit 0 ;;
    *)          die "unknown option: $1" ;;
  esac
done

[ -n "${HOME:-}" ] || die "HOME is not set; cannot determine what to uninstall"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
if [ -n "$PREFIX_OVERRIDE" ]; then APPROOT="$PREFIX_OVERRIDE"; else APPROOT="$DATA_HOME/PyReconstruct"; fi
case "$APPROOT" in /*) ;; *) APPROOT="$PWD/$APPROOT" ;; esac   # absolute (safety check requires it)
APPS_DIR="$DATA_HOME/applications"
HICOLOR="$DATA_HOME/icons/hicolor"
MARKER="$APPROOT/.pyreconstruct-install"
MANIFEST="$APPROOT/.install-manifest"
DEFAULT_LAUNCHER="${XDG_BIN_HOME:-$HOME/.local/bin}/pyreconstruct"
DEFAULT_DESKTOP="$APPS_DIR/pyreconstruct.desktop"
DEFAULT_ICON="$HICOLOR/512x512/apps/pyreconstruct.png"

if [ ! -e "$APPROOT" ] && [ ! -e "$DEFAULT_DESKTOP" ] && [ ! -e "$DEFAULT_LAUNCHER" ]; then
  log "PyReconstruct does not appear to be installed (no $APPROOT)."
  exit 0
fi

removed_any=0
PATH_RC=""

# Remove a single installer-created file (never a directory), with name guards.
remove_file() {
  local p="$1" base
  case "$p" in /*) : ;; *) warn "skipping non-absolute path: $p"; return 0 ;; esac
  base=$(basename -- "$p")
  case "$base" in
    pyreconstruct|pyreconstruct.desktop|pyreconstruct.png) : ;;
    *) warn "skipping unexpected entry: $p"; return 0 ;;
  esac
  if [ -f "$p" ] || [ -L "$p" ]; then
    if rm -f -- "$p"; then note "removed $p"; removed_any=1; else warn "could not remove $p"; fi
  fi
}

# 1) external artifacts (launcher / menu entry / icon)
if [ -f "$MANIFEST" ]; then
  while IFS= read -r line; do
    case "$line" in
      ''|'#'*|prefix\ *) continue ;;
      pathrc\ *) PATH_RC="${line#pathrc }" ;;
      *) remove_file "$line" ;;
    esac
  done <"$MANIFEST"
else
  remove_file "$DEFAULT_LAUNCHER"
  remove_file "$DEFAULT_DESKTOP"
  remove_file "$DEFAULT_ICON"
fi

# 2) a PATH block we added, if any (remove exactly the bounded block, atomically)
if [ -n "$PATH_RC" ] && [ -f "$PATH_RC" ] && grep -Fq '# >>> PyReconstruct >>>' "$PATH_RC"; then
  tmp=$(mktemp "$(dirname -- "$PATH_RC")/.pyrecon-rc.XXXXXX")
  if sed '/# >>> PyReconstruct >>>/,/# <<< PyReconstruct <<</d' "$PATH_RC" >"$tmp"; then
    chmod --reference="$PATH_RC" "$tmp" 2>/dev/null || true   # preserve mode (rc may be 0600)
    mv -- "$tmp" "$PATH_RC"; note "removed PATH block from $PATH_RC"
  else
    rm -f -- "$tmp"
  fi
fi

# 3) the install root, only after passing strict ownership/safety checks
safe_root() {
  local p="$1"
  [ -n "$p" ] || return 1
  case "$p" in /*) : ;; *) return 1 ;; esac            # absolute
  case "$p" in */PyReconstruct) : ;; *) return 1 ;; esac # ends in /PyReconstruct
  [ -L "$p" ] && return 1                               # not a symlink
  case "$p" in
    /|"$HOME"|"$HOME/"|"$HOME/.config"|"$HOME/.local"|"$HOME/.local/share"|"$HOME/.local/bin"|/usr|/etc) return 1 ;;
  esac
  return 0
}

if [ -e "$APPROOT" ]; then
  if safe_root "$APPROOT" && [ -f "$MARKER" ] && [ "$(cat "$MARKER" 2>/dev/null)" = "$APPROOT" ]; then
    rm -rf -- "$APPROOT" && { note "removed $APPROOT"; removed_any=1; }
  else
    warn "refusing to remove $APPROOT (ownership marker missing or failed safety checks)."
    warn "if you are certain it is the PyReconstruct install, remove it by hand."
  fi
fi

# 4) refresh desktop/icon caches (best-effort)
have update-desktop-database && update-desktop-database "$APPS_DIR" >/dev/null 2>&1 || true
have gtk-update-icon-cache && gtk-update-icon-cache -f -t "$HICOLOR" >/dev/null 2>&1 || true

if [ "$removed_any" -eq 1 ]; then log "PyReconstruct uninstalled."; else log "Nothing to remove."; fi
note "Your data (.jser series files and config) was left untouched."
