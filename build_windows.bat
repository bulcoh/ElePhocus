@echo off
REM ElePhocus Windows build - double click to run
cd /d "%~dp0"

if not exist NotoSansKR-Light.ttf (
  echo [ERROR] NotoSansKR-Light.ttf must be in this folder.
  pause
  exit /b 1
)

echo == [1/3] Setting up build environment ==
python -m venv .venv_build
call .venv_build\Scripts\activate.bat
python -m pip install --quiet --upgrade pip
pip install --quiet customtkinter pyinstaller psutil

echo == [2/3] Building (this takes a minute) ==
set ICON=
if exist app_icon.ico set ICON=--icon app_icon.ico
rmdir /s /q build dist 2>nul
del ElePhocus.spec 2>nul
pyinstaller --noconfirm --clean --onefile --windowed --name ElePhocus %ICON% --collect-all customtkinter --add-data "NotoSansKR-Light.ttf;." work_timer.py

echo == [3/3] Done! dist\ElePhocus.exe ==
explorer dist
pause
