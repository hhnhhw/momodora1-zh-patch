@echo off
setlocal
cd /d "%~dp0"
py -3 apply_patch.py --remove
if errorlevel 1 (
  echo Removal stopped. Check the error above. Original game unchanged.
) else (
  echo Patch removed. Run the original momo1_v151.exe.
)
pause
