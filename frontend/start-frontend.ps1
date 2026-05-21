# Start the Next.js frontend on http://localhost:3000
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".\.env.local")) {
    Copy-Item ".\.env.local.example" ".\.env.local"
    Write-Host "Created .env.local from example"
}

if (-not (Test-Path ".\node_modules")) {
    npm install
}

Write-Host "Starting frontend on http://localhost:3000" -ForegroundColor Green
npm run dev
