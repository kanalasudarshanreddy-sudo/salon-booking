# Run the frontend PWA (dev) on http://localhost:5173
# Usage: powershell -ExecutionPolicy Bypass -File .\run-frontend.ps1
$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\frontend"

# Locate Node.js. Adjust if installed elsewhere.
$nodeDir = "C:\Program Files\nodejs"
if (-not (Test-Path "$nodeDir\node.exe")) {
    $cmd = Get-Command node -ErrorAction SilentlyContinue
    if ($cmd) { $nodeDir = Split-Path $cmd.Source } else {
        throw "Node.js not found. Install Node LTS (e.g. winget install OpenJS.NodeJS.LTS)."
    }
}
# Ensure child processes (esbuild, etc.) can find node.
$env:Path = "$nodeDir;" + $env:Path
$npm = "$nodeDir\npm.cmd"

if (-not (Test-Path "node_modules")) {
    Write-Host "Installing dependencies..."
    & $npm install
}

Write-Host "Starting frontend on http://localhost:5173"
& $npm run dev
