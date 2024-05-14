#!/usr/bin/sh

# ENV_DIR provided by Makefile

ENV_BIN=$ENV_DIR/bin
ENV_ETC=$ENV_DIR/etc/conda

#### HOOKS #########################################################################################

echo 'Adding to pre/post-activate hooks...'

scripts_dir=$(realpath .)/scripts

# Make sure shell scripts executable
for script in $scripts_dir/* ; do
  chmod +x $script
done

# Amend activation hooks
for script in env_tweaks/activate/* ; do
  cp $script $ENV_ETC/activate.d/
done

# Add $scripts_dir to path on activation
echo "link_pr_scripts $scripts_dir" >> $ENV_ETC/activate.d/path.sh

# Amend deactivation hooks
for script in env_tweaks/deactivate/* ; do
  cp $script $ENV_ETC/deactivate.d/
done

# Remove $scripts_dir from path on deactivation
deactivate_path=$ENV_ETC/deactivate.d/path.sh
echo "REMOVE=$scripts_dir" | cat - $deactivate_path > temp && mv temp $deactivate_path

echo 'Hooks amended.'

#### SYS.PATH ######################################################################################

echo 'Adding repo to sys.path...'

REPO_PATH=$(realpath ..)
PYTHON=$($ENV_BIN/python -c "import sys; print(f'python{sys.version_info.major}.{sys.version_info.minor}')")
CONDA_PTH=$ENV_DIR/lib/$PYTHON/site-packages/conda.pth

if [ ! -f $CONDA_PTH ] || ! grep -q $REPO_PATH $CONDA_PTH ; then
  echo $REPO_PATH >> $CONDA_PTH
fi

echo 'Repo added to sys.path.'

