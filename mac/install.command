cd ..
echo Creating virtual environment...
python3 -m venv env
source env/bin/activate
echo Installing dependencies...
python3 -m pip install -r src/requirements.txt
echo Finished.