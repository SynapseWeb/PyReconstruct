SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR/../..

echo "Checking for updates..."

git fetch --all
git reset --hard origin/main

# Reset file permissions
chmod u+x launch/mac/run310.command

FILE=env/bin/activate

if [ -f "$FILE" ]; then
    source ./env/bin/activate
else 
    echo "Creating virtual environment..."
    python3.10 -m venv env
    source ./env/bin/activate
fi

echo "Checking dependencies..."
python3.10 -m pip install -r ./src/requirements.txt

echo "Starting PyReconstruct..."
echo "Do NOT close this window while using PyReconstruct!"

python3.10 ./src/PyReconstruct.py
