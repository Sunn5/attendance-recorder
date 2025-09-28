@echo off
setlocal

set "APP_DIR=%~dp0"
if not exist "%APP_DIR%attendance_recorder" (
    echo Could not locate the attendance_recorder package in %APP_DIR%
    exit /b 1
)

start "Attendance Recorder Server" powershell -NoProfile -ExecutionPolicy Bypass -Command ^
 "Set-Location '%APP_DIR%'; python -m attendance_recorder.webapp --store attendance_data.json --host 127.0.0.1 --port 5000"
REM Allow the server a moment to start before opening the browser.
timeout /t 3 >nul
start "" http://127.0.0.1:5000

endlocal
