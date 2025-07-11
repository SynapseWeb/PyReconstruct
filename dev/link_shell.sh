#!/bin/bash
set -euo pipefail

# Ensure ENV_DIR is set
if [[ -z "${ENV_DIR:-}" ]]; then
  echo "Error: ENV_DIR is not set. Please export it or pass it via the Makefile."
  exit 1
fi

ENV_BIN="$ENV_DIR/bin"
ENV_ETC="$ENV_DIR/etc/conda"

mkdir -p "$ENV_ETC/activate.d" "$ENV_ETC/deactivate.d"

#### HOOKS #########################################################################################

echo 'Adding to pre/post-activate hooks...'

# Resolve absolute path to ./scripts (fallback if realpath not installed)
if command -v realpath &> /dev/null; then
  scripts_dir="$(realpath ./scripts)"
else
  scripts_dir="$(cd ./scripts && pwd)"
fi

# Make sure scripts are executable
if [ -d "$scripts_dir" ]; then
  for script in "$scripts_dir"/* ; do
    [ -f "$script" ] && chmod +x "$script"
  done
fi

# Copy activation scripts
if [ -d env_tweaks/activate ]; then
  for script in env_tweaks/activate/* ; do
    [ -f "$script" ] && cp "$script" "$ENV_ETC/activate.d/"
  done
fi

# Add $scripts_dir to PATH on activation
echo "link_pr_scripts \"$scripts_dir\"" >> "$ENV_ETC/activate.d/path.sh"

# Copy deactivation scripts
if [ -d env_tweaks/deactivate ]; then
  for script in env_tweaks/deactivate/* ; do
    [ -f "$script" ] && cp "$script" "$ENV_ETC/deactivate.d/"
  done
fi

# Remove $scripts_dir from PATH on deactivation
deactivate_path="$ENV_ETC/deactivate.d/path.sh"
touch "$deactivate_path"
echo "REMOVE=\"$scripts_dir\"" | cat - "$deactivate_path" > "${deactivate_path}.tmp" && mv "${deactivate_path}.tmp" "$deactivate_path"

echo 'Hooks amended.'

#### SYS.PATH ######################################################################################

echo 'Adding repo to sys.path...'

# Resolve repo path (../ relative to script location)
if command -v realpath &> /dev/null; then
  REPO_PATH="$(realpath ..)"
else
  REPO_PATH="$(cd .. && pwd)"
fi

PYTHON_BIN="$ENV_BIN/python"
if [ ! -x "$PYTHON_BIN" ]; then
  echo "Error: Python binary not found at $PYTHON_BIN"
  exit 1
fi

PYTHON_VER=$("$PYTHON_BIN" -c "import sys; print(f'python{sys.version_info.major}.{sys.version_info.minor}')")
SITE_PKGS="$ENV_DIR/lib/$PYTHON_VER/site-packages"
CONDA_PTH="$SITE_PKGS/conda.pth"

mkdir -p "$SITE_PKGS"

# Add repo path to conda.pth if not already present
if [ ! -f "$CONDA_PTH" ] || ! grep -Fxq "$REPO_PATH" "$CONDA_PTH"; then
  echo "$REPO_PATH" >> "$CONDA_PTH"
fi

echo 'Repo added to sys.path.'

#### sitecustomize.py ##############################################################################

echo 'Adding Python tweaks...'

SITECUSTOM="$SITE_PKGS/sitecustomize.py"
touch "$SITECUSTOM"

# Only add lines if not already present
add_if_missing() {
  local line="$1"
  local file="$2"
  grep -Fq "$line" "$file" || echo "$line" >> "$file"
}

add_if_missing 'import sys' "$SITECUSTOM"
add_if_missing 'from PyReconstruct.modules.datatypes.series import Series' "$SITECUSTOM"
add_if_missing 'sys.modules["__main__"].open_series = Series.openJser' "$SITECUSTOM"

echo 'Tweaks done!'
