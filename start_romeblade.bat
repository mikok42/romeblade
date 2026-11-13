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

echo Starting RomeBlade bridge (minimized log: out\bridge_run.log) ...
start "RomeBlade bridge" /MIN cmd /c "python -m tools.romeblade_bridge >> out\bridge_run.log 2>&1"

REM Brief pause so the hook is up before Rome grabs the mouse.
timeout /t 2 /nobreak >nul

echo Starting Rome: Total War (normal / fullscreen) ...
start "" /D "C:\Program Files (x86)\Steam\steamapps\common\Rome Total War Gold" "C:\Program Files (x86)\Steam\steamapps\common\Rome Total War Gold\RomeTW.exe"

echo.
echo Bridge is watching. Load your campaign, fight as usual until the
echo pre-battle scroll, then click Begin Battle once.
echo When you quit Rome, the bridge should exit by itself.
echo.
endlocal
