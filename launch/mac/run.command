cd "$(dirname "$0")"
cd ../..
echo Checking for updates...
git fetch
git pull
FILE=env/bin/activate
if [ -f "$FILE" ]; then
    source env/bin/activate
else 
    echo Creating virtual environment...
    python3.10 -m venv env
    source env/bin/activate
fi
echo Checking dependencies...
python3 -m pip install -r src/requirements.txt
echo Starting PyReconstruct...
echo Do NOT close this window while using PyReconstruct!
python3 src/PyReconstruct.py $1
