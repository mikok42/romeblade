@echo off
REM RomeBlade everyday starter: bridge in background, Rome as you normally play
REM (fullscreen — no -ne). You load the campaign and open the battle scroll;
REM the bridge only waits for the pre-battle panel and Begin Battle.
REM
REM Closing Rome exits the bridge and clears the mouse hook.
REM Do not run this while another agent is driving the mouse.

setlocal
cd /d "%~dp0"

if not exist "out" mkdir "out"

echo Starting RomeBlade bridge (logs: out\bridge_run.log + out\bridge_events.log) ...
start "RomeBlade bridge" /MIN cmd /c "python -m tools.romeblade_bridge >> out\bridge_run.log 2>&1"

REM Brief pause so the bridge process is up before Rome starts.
timeout /t 2 /nobreak >nul

echo Starting Rome: Total War (normal / fullscreen) ...
start "" /D "C:\Program Files (x86)\Steam\steamapps\common\Rome Total War Gold" "C:\Program Files (x86)\Steam\steamapps\common\Rome Total War Gold\RomeTW.exe"

echo.
echo 1. Load your campaign and open a land battle scroll.
echo 2. Press F5 once (arms the mouse hook — needed if fullscreen GDI fails).
echo 3. Click Begin Battle.
echo Do NOT close the minimized "RomeBlade bridge" window before the fight.
echo Events: out\bridge_events.log   When you quit Rome, the bridge exits.
echo.
endlocal
