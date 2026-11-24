@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0Momodora1ZH_Setup.exe" (
  start "" /d "%~dp0.." "%~dp0Momodora1ZH_Setup.exe"
  exit /b 0
)
where py >nul 2>nul
if errorlevel 1 (
  echo Python 3 is required. Install Python 3 and run this file again.
  pause
  exit /b 1
)
py -3 apply_patch.py
if errorlevel 1 (
  echo Installation failed. The original game was not overwritten.
) else (
  echo Installation complete. Run momo1_v151_zh.exe in the game folder.
)
pause
