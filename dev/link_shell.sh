#!/usr/bin/sh

ENV_BIN=$1
SHELL_SCRIPTS=$(ls shell)

echo 'Linking shell scripts to environment bin...'

for script in $SHELL_SCRIPTS ; do
  ENV_SCRIPT=$ENV_BIN/$script
  if [[ -f $ENV_SCRIPT ]] ; then rm $ENV_SCRIPT ; fi
  cp shell/$script $ENV_BIN/
  chmod +x $ENV_SCRIPT
done

echo 'Shell scripts available in environment bin directory.'
