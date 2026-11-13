@echo off
REM RomeBlade: bridge + Rome WINDOWED (-ne). No Arm panel — GDI scroll detect arms the hook.
REM Exclusive fullscreen blocks GDI; that is why we use -ne. F5 remains a manual backup.

setlocal
cd /d "%~dp0"
if not exist "out" mkdir "out"

echo [1/2] Bridge (log: out\bridge_events.log) ...
start "RomeBlade bridge" /MIN cmd /c "python -m tools.romeblade_bridge >> out\bridge_run.log 2>&1"
timeout /t 1 /nobreak >nul

echo [2/2] Rome WINDOWED (-ne) ...
start "" /D "C:\Program Files (x86)\Steam\steamapps\common\Rome Total War Gold" ^
  "C:\Program Files (x86)\Steam\steamapps\common\Rome Total War Gold\RomeTW.exe" -ne -show_err

echo.
echo JEDNA INSTRUKCJA:
echo   Otworz zwój przed bitwa — bridge sam uzbraja hak (GDI). Kliknij Begin Battle.
echo   Rome NIE moze otworzyc wlasnej bitwy; ma startowac M&B (RomeBladeRTS).
echo   Potem w M&B: Graj -^> Nowa gra -^> Wave Battle (sklad z zapisu RTW).
echo   Nie zamykaj okna "RomeBlade bridge". F5 = awaryjne uzbrojenie.
echo.
endlocal
