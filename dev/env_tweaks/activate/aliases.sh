PYRECON_ALIASES=()

define_alias(){
  if alias $1 >/dev/null 2>&1; then 
    :  # if alias already exists, don't overwrite it
  else 
    alias $1="$2"
    PYRECON_ALIASES+=($1)
  fi
}

# Make sure to quote commands with mutiple parts that are separated by whitespace
define_alias PyReconstruct "python -m PyReconstruct.run"
define_alias pyrecon PyReconstruct
define_alias pr PyReconstruct
define_alias ng neuroglancer

export PYRECON_ALIASES
