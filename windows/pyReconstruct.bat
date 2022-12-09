@echo off
cd /D "%~dp0"
call ..\env\Scripts\activate
START /B /WAIT cmd /c python ../src/pyReconstruct.py %1
call deactivate
echo Press enter to exit.
pause>nul
