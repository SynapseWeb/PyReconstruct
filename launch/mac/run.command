SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR/../..

echo "Checking for updates..."

git fetch
git pull

FILE=env/bin/activate

if [ -f "$FILE" ]; then
    source ./env/bin/activate
else 
    echo "Creating virtual environment..."
    python3 -m venv env
    source ./env/bin/activate
fi

echo "Checking dependencies..."
python3 -m pip install -r ./src/requirements.txt

echo "Starting PyReconstruct..."
echo "Do NOT close this window while using PyReconstruct!"

python3 ./src/PyReconstruct.py
