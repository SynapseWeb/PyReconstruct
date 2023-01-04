#!/usr/bin/env bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

cd $SCRIPT_DIR/..

if [ ! -f "env/bin/activate" ]; then
    python -m venv env
    source env/bin/activate
    pip install --upgrade pip
    deactivate
fi

source env/bin/activate
pip install -r src/requirements.txt
python src/PyReconstruct.py
