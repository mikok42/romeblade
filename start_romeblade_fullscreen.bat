@echo off
REM Fullscreen Rome — GDI scroll detect often FAILS (black capture). Prefer start_romeblade.bat (-ne).
REM No Arm panel. F5 may also fail under exclusive FS.

setlocal
cd /d "%~dp0"
if not exist "out" mkdir "out"

start "RomeBlade bridge" /MIN cmd /c "python -m tools.romeblade_bridge >> out\bridge_run.log 2>&1"
timeout /t 1 /nobreak >nul
start "" /D "C:\Program Files (x86)\Steam\steamapps\common\Rome Total War Gold" ^
  "C:\Program Files (x86)\Steam\steamapps\common\Rome Total War Gold\RomeTW.exe"

echo Lepiej uzyj start_romeblade.bat (Rome -ne). Tu GDI/F5 czesto nie dziala.
endlocal
