@echo off
setlocal

IF "%1"=="prod" (
    echo Starting in production mode...
    cd frontend
    call npm run build
    start /B npm run start
    cd ..\backend\byteport
    go run main.go
) ELSE IF "%1"=="dev" (
    echo Starting in development mode...

    REM Check if tmux is available (for WSL users)
    where tmux >nul 2>nul
    IF %ERRORLEVEL% EQU 0 (
        REM WSL/tmux version
        tmux new-session -d -s devsession
        tmux split-window -h
        tmux select-pane -t 0
        tmux send-keys "cd frontend && npm run dev -- --port 5173" C-m
        tmux select-pane -t 1
        tmux send-keys "cd backend/byteport && air" C-m
        tmux attach-session -t devsession
    ) ELSE (
        REM Pure Windows version using multiple command prompts
        echo Starting frontend...
        start cmd /k "cd frontend && npm run dev -- --port 5173"
        
        echo Starting backend...
        start cmd /k "cd backend\byteport && air"
    )
) ELSE (
    echo Usage: %0 {dev^|prod}
    exit /b 1
)

endlocal