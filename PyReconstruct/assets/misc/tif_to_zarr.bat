@echo off
cd /D "%~dp0"
cd ../../..
call env\Scripts\activate
START /B /WAIT cmd /c python src/assets/misc/tif_to_zarr.py
call deactivate
echo Press enter to exit.
pause>nul
