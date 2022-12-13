cd "$(dirname "$0")"
cd ..
FILE=env/bin/activate
if [ -f "$FILE" ]; then
    source env/bin/activate
else 
    echo Creating virtual environment...
    python3 -m venv env
    source env/bin/activate
fi
echo Checking dependencies...
python3 -m pip install -r src/requirements.txt
echo Starting PyReconstruct...
python3 src/pyReconstruct.py $1