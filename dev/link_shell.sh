#!/usr/bin/sh

ENV_DIR=$1
ENV_BIN=$ENV_DIR/bin
ENV_ETC=$ENV_DIR/etc/conda

#### SHELL SCRIPTS #############################################################

echo 'Linking shell scripts to environment bin...'

SHELL_SCRIPTS=$(ls shell)

for script in $SHELL_SCRIPTS ; do
  ENV_SCRIPT=$ENV_BIN/$script
  if [[ -f $ENV_SCRIPT ]] ; then rm $ENV_SCRIPT ; fi
  cp shell/$script $ENV_BIN/
  chmod +x $ENV_SCRIPT
done

echo 'Shell scripts available in environment bin directory.'

#### HOOKS #####################################################################

echo 'Adding to pre/post-activate hooks...'

for script in env_tweaks/activate/* ; do
  cp $script $ENV_ETC/activate.d/
done

for script in env_tweaks/deactivate/* ; do
  cp $script $ENV_ETC/deactivate.d/
done

echo 'Hooks amended...'

