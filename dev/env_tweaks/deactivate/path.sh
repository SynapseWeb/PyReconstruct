WORK=:$PATH:
WORK=${WORK/:$REMOVE:/:}
WORK=${WORK%:}
WORK=${WORK#:}
export PATH=$WORK
