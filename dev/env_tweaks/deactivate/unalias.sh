for i in ${PYRECON_ALIASES[@]}
do
  unalias $i
done

unset PYRECON_ALIASES
