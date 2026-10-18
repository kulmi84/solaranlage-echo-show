@echo off
cd /d "%~dp0"
py -3 setup_app.py
if errorlevel 1 (
  echo Bitte Python 3 mit Tcl/Tk installieren. Alternativ: python setup_app.py
  pause
)
