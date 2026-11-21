@echo off
cd /d "%~dp0"
if not exist "momo1_v151_zh.exe" (
  echo Localized executable not found. Install the patch first.
  pause
  exit /b 1
)
start "" /d "%~dp0" "%~dp0momo1_v151_zh.exe"
