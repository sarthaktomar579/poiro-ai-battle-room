# Start the Poiro FastAPI backend on http://localhost:8000
# Prefer Python 3.13 (.venv313) — Python 3.14 may compile pydantic-core from source.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$venv = if (Test-Path ".\.venv313\Scripts\python.exe") { ".\.venv313" }
        elseif (Test-Path ".\.venv\Scripts\python.exe") { ".\.venv" }
        else { $null }

if (-not $venv) {
    Write-Host "Creating virtualenv with Python 3.13..."
    py -3.13 -m venv .venv313
    $venv = ".\.venv313"
}

& "$venv\Scripts\Activate.ps1"
pip install -r requirements.txt
python -m app.seed
Write-Host ""
Write-Host "Starting API on http://localhost:8000" -ForegroundColor Green
Write-Host "Keep this window open while using the frontend on http://localhost:3000" -ForegroundColor Yellow
# Only watch app/ — avoids reload storms when pip writes into .venv
uvicorn app.main:app --reload --reload-dir app --port 8000
