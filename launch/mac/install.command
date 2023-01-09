echo "Installing PyReconstruct..."

# Change dir to install script dir
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR

# Git clone repo
git clone https://github.com/SynapseWeb/PyReconstruct

# Switch to neu466g branch
cd ./PyReconstruct

# Change permissions to launch scripts
chmod u+x ./launch/mac/run.command

# Make virtual environment and install dependencies
python -m venv env
source ./env/bin/activate
pip install -r ./src/requirements.txt
deactivate

echo "Installation complete. Please close this window."
