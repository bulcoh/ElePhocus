#!/bin/bash
# ElePhocus Mac build - double click to run
cd "$(dirname "$0")"
set -e

echo "== [1/4] Setting up build environment =="
python3 -m venv .venv_build
source .venv_build/bin/activate
pip install --quiet --upgrade pip
pip install --quiet customtkinter pyinstaller pyobjc-framework-Cocoa pyobjc-framework-Quartz

echo "== [2/4] Building (this takes a minute) =="
ICON=""
[ -f app_icon.icns ] && ICON="--icon app_icon.icns"
rm -rf build dist ElePhocus.spec
pyinstaller --noconfirm --clean --windowed --name ElePhocus $ICON \
  --osx-bundle-identifier com.redelephant.elephocus \
  --collect-all customtkinter \
  work_timer.py

echo "== [3/4] Writing app info =="
PLIST="dist/ElePhocus.app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Add :CFBundleShortVersionString string 1.1" "$PLIST" 2>/dev/null || \
/usr/libexec/PlistBuddy -c "Set :CFBundleShortVersionString 1.1" "$PLIST"
/usr/libexec/PlistBuddy -c "Add :NSHumanReadableCopyright string © 2025 붉은코끼리. All rights reserved." "$PLIST" 2>/dev/null || true
[ -f License.txt ] && cp License.txt dist/ElePhocus.app/Contents/Resources/
codesign --force --deep --sign - dist/ElePhocus.app 2>/dev/null || true

echo "== [4/4] Done! =="
file dist/ElePhocus.app/Contents/MacOS/ElePhocus
open dist
