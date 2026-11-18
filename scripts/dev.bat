@echo off
setlocal enabledelayedexpansion

REM Ensure we run from the project root directory
cd /d "%~dp0\.."

echo ========================================================
echo        XakuFinance - Local Development Launcher
echo ========================================================
echo.

REM 1. Check Python virtual environment
if not exist "backend\.venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found at backend\.venv\Scripts\python.exe
    echo Please make sure backend dependencies are installed.
    pause
    exit /b 1
)

REM 2. Run Database Migrations
echo [1/3] Applying database migrations...
backend\.venv\Scripts\python.exe backend\manage.py migrate
if errorlevel 1 (
    echo [ERROR] Database migrations failed. Is PostgreSQL running on port 5432?
    pause
    exit /b 1
)

REM Ensure demo account and workspace are initialized
backend\.venv\Scripts\python.exe backend\manage.py seed_workspace

REM 3. Start Backend Django API Server in a new window
echo [2/3] Starting Backend API Server (http://127.0.0.1:8000)...
start "XakuFinance Backend [8000]" cmd /k "backend\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000"

REM 4. Start Frontend Vite Dev Server in a new window
echo [3/3] Starting Frontend Dev Server (http://localhost:5173)...
start "XakuFinance Frontend [5173]" cmd /k "cd frontend && npm run dev"

echo.
echo ========================================================
echo   Services are starting up in separate windows!
echo.
echo   - Web Application: http://localhost:5173
echo   - Interactive API: http://127.0.0.1:8000/api/docs/
echo.
echo   Demo Login:
echo     Email:    demo@xakufinance.local
echo     Password: DemoPass123456
echo ========================================================
echo.
pause
