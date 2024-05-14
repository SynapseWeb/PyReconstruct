link_pr_scripts() {
  if [ -d $1 ] && [[ ":$PATH:" != *":$1:"* ]]; then
    export PATH="$1${PATH:+":$PATH"}"
  fi
}

