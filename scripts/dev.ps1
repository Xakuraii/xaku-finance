# Set directory to project root
Set-Location "$PSScriptRoot\.."

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "       XakuFinance - Local Development Launcher         " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path "backend\.venv\Scripts\python.exe")) {
    Write-Host "[ERROR] Virtualenv not found at backend\.venv\Scripts\python.exe" -ForegroundColor Red
    exit 1
}

Write-Host "[1/3] Applying database migrations..." -ForegroundColor Yellow
& "backend\.venv\Scripts\python.exe" backend\manage.py migrate
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Database migrations failed. Please check PostgreSQL." -ForegroundColor Red
    exit 1
}

Write-Host "[2/3] Launching Backend API server (http://127.0.0.1:8000)..." -ForegroundColor Yellow
Start-Process cmd -ArgumentList "/k", "title XakuFinance Backend [8000] & backend\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000"

Write-Host "[3/3] Launching Frontend dev server (http://localhost:5173)..." -ForegroundColor Yellow
Start-Process cmd -ArgumentList "/k", "title XakuFinance Frontend [5173] & cd frontend & npm run dev"

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "  Services launched successfully!" -ForegroundColor Green
Write-Host "  - Web App:       http://localhost:5173" -ForegroundColor Green
Write-Host "  - Swagger Docs:  http://127.0.0.1:8000/api/docs/" -ForegroundColor Green
Write-Host ""
Write-Host "  Demo Credentials:" -ForegroundColor Green
Write-Host "    Email:    demo@xakufinance.local" -ForegroundColor Green
Write-Host "    Password: DemoPass123456!" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host ""
