@echo off
cd /D "%~dp0"
cd ../..
echo Checking for updates...
git fetch --all
git reset --hard origin/main
echo Starting virtual environment...
if exist env\Scripts\activate (
   echo Starting previously created environment...
   call env\Scripts\activate
) else (
    echo Creating virtual environment...
    START /B /WAIT cmd /c python -m venv env
    call env\Scripts\activate
    @timeout /t 1 /nobreak > nul
)
echo Checking dependencies...
START /B /WAIT cmd /c pip install -r requirements.txt
echo Starting PyReconstruct...
echo Do NOT close this window while using PyReconstruct!
START /B /WAIT cmd /c python PyReconstruct/run.py %1
call deactivate
echo Press enter to exit.
pause>nul
