# Start the Poiro FastAPI backend on http://localhost:8000
# Uses the venv's python.exe directly (no Activate.ps1 required).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Test-VenvReady($path) {
    return (Test-Path "$path\Scripts\python.exe")
}

$venv = $null
foreach ($candidate in @(".\.venv313", ".\.venv")) {
    if (Test-VenvReady $candidate) {
        $venv = $candidate
        break
    }
}

if (-not $venv) {
    Write-Host "Creating virtualenv with Python 3.13 (.venv313)..." -ForegroundColor Yellow
    py -3.13 -m venv .venv313
    if (-not (Test-VenvReady ".\.venv313")) {
        Write-Host "Trying default python -m venv .venv ..." -ForegroundColor Yellow
        python -m venv .venv
        $venv = ".\.venv"
    } else {
        $venv = ".\.venv313"
    }
}

$py = Join-Path $venv "Scripts\python.exe"
$pip = Join-Path $venv "Scripts\pip.exe"

Write-Host "Using venv: $venv" -ForegroundColor Cyan

& $pip install -r requirements.txt
& $py -m app.seed

Write-Host ""
Write-Host "Starting API on http://localhost:8000" -ForegroundColor Green
Write-Host "Keep this window open while using the frontend on http://localhost:3000" -ForegroundColor Yellow

& $py -m uvicorn app.main:app --reload --reload-dir app --port 8000
