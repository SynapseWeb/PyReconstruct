@echo off
echo Installing PyReconstruct...
git clone https://github.com/SynapseWeb/PyReconstruct.git
cd PyReconstruct
echo Creating virtual environment...
START /B /WAIT cmd /c python -m venv env
call env\Scripts\activate
@timeout /t 1 /nobreak > nul
echo Installing dependencies...
START /B /WAIT cmd /c pip install -r src/requirements.txt
call deactivate
echo Press enter to exit.
pause>nul
