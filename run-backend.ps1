# Run the backend API (dev) on http://127.0.0.1:8000
# Usage: powershell -ExecutionPolicy Bypass -File .\run-backend.ps1
$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\backend"

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
    & ".venv\Scripts\python.exe" -m pip install --upgrade pip
    & ".venv\Scripts\python.exe" -m pip install -r requirements.txt
}

# Seed the database if it doesn't exist yet.
if (-not (Test-Path "salon.db")) {
    Write-Host "Seeding database..."
    & ".venv\Scripts\python.exe" -m app.seed
}

Write-Host "Starting API on http://127.0.0.1:8000 (docs at /docs)"
& ".venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000
