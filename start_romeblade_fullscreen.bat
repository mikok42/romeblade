@echo off
REM Fullscreen Rome — F5 usually does NOT reach the bridge. Use Arm panel after Alt+Tab.
REM Prefer start_romeblade.bat (-ne).

setlocal
cd /d "%~dp0"
if not exist "out" mkdir "out"

start "RomeBlade bridge" /MIN cmd /c "python -m tools.romeblade_bridge >> out\bridge_run.log 2>&1"
timeout /t 1 /nobreak >nul
start "RomeBlade Arm" pythonw -m tools.romeblade_bridge.arm_panel
timeout /t 1 /nobreak >nul
start "" /D "C:\Program Files (x86)\Steam\steamapps\common\Rome Total War Gold" ^
  "C:\Program Files (x86)\Steam\steamapps\common\Rome Total War Gold\RomeTW.exe"

echo Zwój -^> Alt+Tab -^> UZBROJ -^> z powrotem do Rome -^> Begin Battle.
echo Lepiej: start_romeblade.bat (okno -ne).
endlocal
