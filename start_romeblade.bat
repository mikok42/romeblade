@echo off
REM RomeBlade: bridge + Arm panel + Rome WINDOWED (-ne on CLI only, prefs untouched).
REM Exclusive fullscreen blocks F5 — that is why we use -ne and a visible Arm button.

setlocal
cd /d "%~dp0"
if not exist "out" mkdir "out"

echo [1/3] Bridge (log: out\bridge_events.log) ...
start "RomeBlade bridge" /MIN cmd /c "python -m tools.romeblade_bridge >> out\bridge_run.log 2>&1"
timeout /t 1 /nobreak >nul

echo [2/3] Arm panel (always on top) ...
start "RomeBlade Arm" pythonw -m tools.romeblade_bridge.arm_panel
timeout /t 1 /nobreak >nul

echo [3/3] Rome WINDOWED (-ne) ...
start "" /D "C:\Program Files (x86)\Steam\steamapps\common\Rome Total War Gold" ^
  "C:\Program Files (x86)\Steam\steamapps\common\Rome Total War Gold\RomeTW.exe" -ne -show_err

echo.
echo JEDNA INSTRUKCJA:
echo   Zwój przed bitwa -^> kliknij UZBROJ w oknie RomeBlade -^> Begin Battle w Rome.
echo   Rome NIE moze otworzyc wlasnej bitwy; ma startowac M&B.
echo   Nie zamykaj okien "RomeBlade bridge" ani "RomeBlade Arm".
echo.
endlocal
