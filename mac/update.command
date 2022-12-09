cd ..
echo Updating repository...
git fetch
git pull
echo Updating dependencies...
source env/Scripts/activate
python3 -m pip install -r src/requirements.txt
echo Finished.
