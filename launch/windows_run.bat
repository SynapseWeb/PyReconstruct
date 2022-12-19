@echo off
cd /D "%~dp0"
cd ..
echo Checking for updates...
git fetch
git pull
if exist env\Scripts\activate (
    call env\Scripts\activate
) else (
    echo Creating virtual environment...
    START /B /WAIT cmd /c python3.10 -m venv env
    call env\Scripts\activate
    @timeout /t 1 /nobreak > nul
)
echo Checking dependencies...
START /B /WAIT cmd /c pip install -r src/requirements.txt
echo Starting PyReconstruct...
START /B /WAIT cmd /c python src/pyReconstruct.py %1
call deactivate
echo Press enter to exit.
pause>nul