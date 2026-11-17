@echo off
REM ElePhocus Windows build - double click to run
cd /d "%~dp0"

set FONTS=
if exist fonts (
  set FONTS=--add-data "fonts;fonts"
) else (
  echo [WARN] "fonts" folder not found - the app will fall back to Malgun Gothic.
)

echo == [1/3] Setting up build environment ==
python -m venv .venv_build
call .venv_build\Scripts\activate.bat
python -m pip install --quiet --upgrade pip
pip install --quiet customtkinter pyinstaller psutil pillow certifi

echo == [2/3] Building (this takes a minute) ==
REM make app_icon.ico from icon.png if there is no .ico yet
if not exist app_icon.ico if exist icon.png python make_ico.py icon.png app_icon.ico

set ICON=
set ICONDATA=
if exist app_icon.ico (
  set ICON=--icon app_icon.ico
  set ICONDATA=--add-data "app_icon.ico;."
) else (
  echo [WARN] No app_icon.ico / icon.png - building without a custom icon.
)
rmdir /s /q build dist 2>nul
del ElePhocus.spec 2>nul
pyinstaller --noconfirm --clean --onefile --windowed --name ElePhocus %ICON% %ICONDATA% %FONTS% --collect-all customtkinter work_timer.py

echo == [3/3] Done! dist\ElePhocus.exe ==
explorer dist
pause
