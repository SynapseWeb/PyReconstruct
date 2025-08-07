#!/usr/bin/sh

# ENV_DIR provided by Makefile

ENV_BIN=$ENV_DIR/bin
ENV_ETC=$ENV_DIR/etc/conda

#### HOOKS #########################################################################################

echo 'Adding to pre/post-activate hooks...'

# Get absolute path in a cross-platform way 
if command -v realpath >/dev/null 2>&1; then
    scripts_dir=$(realpath .)/scripts
elif command -v greadlink >/dev/null 2>&1; then
    # GNU coreutils readlink (available via homebrew on macOS)
    scripts_dir=$(greadlink -f .)/scripts
else
    # Fallback for systems without realpath/greadlink
    scripts_dir=$(cd . && pwd)/scripts
fi

# Make sure shell scripts executable
for script in $scripts_dir/* ; do
  [ -f "$script" ] && chmod +x $script
done

# Create activation/deactivation directories if they do not exist
mkdir -p "$ENV_ETC/activate.d"
mkdir -p "$ENV_ETC/deactivate.d"

# Amend activation hooks
if [ -d "env_tweaks/activate" ]; then
    for script in env_tweaks/activate/* ; do
        [ -f "$script" ] && cp "$script" "$ENV_ETC/activate.d/"
    done
fi

# Add $scripts_dir to path on activation
echo "link_pr_scripts $scripts_dir" >> $ENV_ETC/activate.d/path.sh

# Amend deactivation hooks
if [ -d "env_tweaks/deactivate" ]; then
    for script in env_tweaks/deactivate/* ; do
        [ -f "$script" ] && cp "$script" "$ENV_ETC/deactivate.d/"
    done
fi

# Remove $scripts_dir from path on deactivation
deactivate_path="$ENV_ETC/deactivate.d/path.sh"
if [ -f "$deactivate_path" ]; then
    echo "REMOVE=$scripts_dir" | cat - "$deactivate_path" > temp && mv temp "$deactivate_path"
else
    echo "REMOVE=$scripts_dir" > "$deactivate_path"
fi

echo 'Hooks amended.'

#### SYS.PATH ######################################################################################

echo 'Adding repo to sys.path...'

# Get absolute path in a cross-platform way 
if command -v realpath >/dev/null 2>&1; then
    REPO_PATH=$(realpath ..)
elif command -v greadlink >/dev/null 2>&1; then
    REPO_PATH=$(greadlink -f ..)
else
    REPO_PATH=$(cd .. && pwd)
fi

PYTHON=$("$ENV_BIN/python" -c "import sys; print(f'python{sys.version_info.major}.{sys.version_info.minor}')")
SITE_PKGS="$ENV_DIR/lib/$PYTHON/site-packages"
CONDA_PTH="$SITE_PKGS/conda.pth"

# Create site-packages directory if it doesn't exist
mkdir -p "$SITE_PKGS"

if [ ! -f $CONDA_PTH ] || ! grep -q $REPO_PATH $CONDA_PTH ; then
  echo $REPO_PATH >> $CONDA_PTH
fi

echo 'Repo added to sys.path.'

echo 'Adding Python tweaks...'

# Create or append to sitecustomize.py
{
    echo 'import sys'
    echo 'from PyReconstruct.modules.datatypes.series import Series'
    echo 'sys.modules["__main__"].open_series = Series.openJser'
} >> "$SITE_PKGS/sitecustomize.py"

echo 'Tweaks done!'
