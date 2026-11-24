@echo off
REM AgilePlus — Windows launcher
setlocal
set AP_HOME=E:\phase-finish-stack\AgilePlus
cd /d "%AP_HOME%"

echo === AgilePlus launcher ===
echo Starting process-compose stack...

where process-compose >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    process-compose up -f process-compose.yml
    goto :open
)

REM Fallback: bring up subsystems individually
if exist "%AP_HOME%\apps\byteport\package.json" (
    start "byteport" cmd /k "cd /d %AP_HOME%\apps\byteport && npm run dev"
)
if exist "%AP_HOME%\desktop\electrobun" (
    start "electrobun" cmd /k "cd /d %AP_HOME%\desktop\electrobun && bun run dev"
)

:open
timeout /t 4 >nul
start "" http://localhost:3000
echo Stack started. Press any key to detach.
pause >nul
endlocal
