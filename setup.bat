@echo off
TITLE PFAMS - Setup & Installation
echo ===================================================
echo   Personal Financial Analytics & Management System
echo   Automated Environment Setup & Installation
echo ===================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found on your PATH.
    echo Please install Python 3.10+ and check "Add Python to PATH".
    pause
    exit /b 1
)

echo [1/5] Creating Python virtual environment...
if not exist "venv" (
    python -m venv venv
    echo Virtual environment created at .\venv\
) else (
    echo Virtual environment already exists at .\venv\
)

echo [2/5] Upgrading pip and installing requirements...
.\venv\Scripts\python -m pip install --upgrade pip
.\venv\Scripts\pip install -r requirements.txt

echo [3/5] Setting up environment configuration...
if not exist ".env" (
    copy .env.example .env
    echo Created .env from .env.example
) else (
    echo .env configuration file found.
)

echo [4/5] Running database migrations...
.\venv\Scripts\python manage.py makemigrations
.\venv\Scripts\python manage.py migrate

echo [5/5] Seeding default categories and demo data...
.\venv\Scripts\python manage.py seed_data --demo

echo.
echo ===================================================
echo   PFAMS Setup Completed Successfully!
echo ===================================================
echo   You can now launch the application by running:
echo   run.bat
echo ===================================================
echo.
pause
