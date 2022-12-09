@echo off
cd ..
echo Updating dependencies...
call env\Scripts\activate
@timeout /t 1 /nobreak > nul
START /B /WAIT cmd /c pip install -r src/requirements.txt
call deactivate
cd windows
echo Finished.
echo Press enter to exit.
pause>nul
