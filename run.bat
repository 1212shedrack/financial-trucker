@echo off
TITLE PFAMS - Server
echo ===================================================
echo   Starting PFAMS (Personal Financial Management)
echo ===================================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo Please run setup.bat first to install the system.
    pause
    exit /b 1
)

echo Starting development server on http://127.0.0.1:8000/ ...
echo (Press CTRL+C to stop the server)
echo.

start "" "http://127.0.0.1:8000/"
.\venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
pause
