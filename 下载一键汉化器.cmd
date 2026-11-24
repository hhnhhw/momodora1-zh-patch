@echo off
setlocal
cd /d "%~dp0"
if not exist "%~dp0Momo1_151_Chinese_Patch\Momodora1ZH_Setup.exe" (
  echo Momodora1ZH_Setup.exe is missing. Re-download the complete release.
  pause
  exit /b 1
)
echo Starting the standalone Momodora 1.51 Chinese patcher.
start "" /d "%~dp0" "%~dp0Momo1_151_Chinese_Patch\Momodora1ZH_Setup.exe"
