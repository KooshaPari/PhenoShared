@echo off
setlocal enabledelayedexpansion

set BASE=integration/consolidate

echo === BRANCH TRIAGE vs %BASE% ===
echo.
echo | branch                                        | commits_ahead | deletions   | status          |
echo |---------------------------------------------|-------------|-----------|---------------|

for /f "delims=" %%b in (_branches.txt) do (
    set "branch=%%b"
    
    rem Get commits ahead
    for /f "delims=" %%a in ('git rev-list --count %BASE%..%%b 2^>nul') do set "ahead=%%a"
    if not defined ahead set "ahead=0"
    
    rem Get deletions count
    for /f "delims=" %%d in ('git diff --name-status %BASE%..%%b 2^>nul ^| find /c "^D"') do set "dels=%%d"
    if not defined dels set "dels=0"
    
    rem Determine status
    if !ahead! gtr 0 (
        if !dels! equ 0 (
            set "status=MERGE-READY"
        ) else (
            set "status=SKIP-DEL"
        )
    ) else (
        set "status=ALREADY-MERGED"
    )
    
    echo | !branch!                              | !ahead!           | !dels!          | !status!        |
)

echo.
echo === MERGE-READY branches: commit subjects ===
echo.

for /f "delims=" %%b in (_branches.txt) do (
    set "branch=%%b"
    for /f "delims=" %%a in ('git rev-list --count %BASE%..%%b 2^>nul') do set "ahead=%%a"
    if not defined ahead set "ahead=0"
    for /f "delims=" %%d in ('git diff --name-status %BASE%..%%b 2^>nul ^| find /c "^D"') do set "dels=%%d"
    if not defined dels set "dels=0"
    
    if !ahead! gtr 0 (
        if !dels! equ 0 (
            echo --- %%b (!ahead! commits, !dels! deletions) ---
            git log --oneline %BASE%..%%b
            echo.
        )
    )
)
