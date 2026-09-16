@echo off
REM scripts/_install_wsl_direct.bat
REM Direct WSL launcher — bypasses PowerShell Start-Process redirect-blocking bug.
REM Runs the bootstrap script inside WSL Ubuntu-22.04 and writes all output
REM (stdout+stderr) to the heartbeat log. No HF_TOKEN is needed for the
REM bootstrap itself; that's only for the weight download step.

setlocal
set TS=%date:~10,4%-%date:~4,2%-%date:~7,2%T%time:~0,2%-%time:~3,2%-%time:~6,2%Z
set TS=%TS: =0%
set LOG_DIR=C:\Users\koosh\pheno-harness\bench\results\2026-07-04
set HEARTBEAT=%LOG_DIR%\_wsl_install_heartbeat.json
set LOG_FILE=%LOG_DIR%\_wsl_install_%TS%.log
set PHENO_ROOT=/mnt/c/Users/koosh/pheno-harness
set SH_SCRIPT=%PHENO_ROOT%/scripts/install_wsl_pheno_serve.sh

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM Truly-detached wsl launch via cmd /c start /b. Stdout+stderr to log file.
REM We use the .sh directly with `bash -lc` for a login-shell that boots init.d.
start /b "" wsl -d Ubuntu-22.04 -- bash -lc "%SH_SCRIPT%" >"%LOG_FILE%" 2>&1

REM Write a pre-heartbeat so callers can see we launched
echo {"step":"launch","status":"ok","message":"bootstrap detached via wsl -e bash","timestamp":"%TS%","log_file":"%LOG_FILE%"} > "%HEARTBEAT%"

echo WSL bootstrap detached; PID will appear in %LOG_FILE%
echo Heartbeat: %HEARTBEAT%
echo Full log:  %LOG_FILE%
endlocal
