@echo off
set BASE=%~dp0
echo [SStock] Launching backend and frontend in separate windows...
start "SStock Backend" cmd /k ""%BASE%start_backend.bat""
start "SStock Frontend" cmd /k ""%BASE%start_frontend.bat""
echo [SStock] Backend:  http://127.0.0.1:8000
echo [SStock] Frontend: http://localhost:5173
echo [SStock] Close those windows or run stop.bat to stop.
