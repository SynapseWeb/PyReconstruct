@echo off
call ..\env\Scripts\activate
START /B /WAIT cmd /c python ../src/pyReconstruct.py
call deactivate
