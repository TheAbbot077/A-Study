Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "=============================="
Write-Host "Resetting Docker environment"
Write-Host "=============================="

Write-Host "Stopping containers..."
docker compose down

Write-Host "Building containers..."
docker compose build

Write-Host "Starting containers..."
docker compose up -d

Write-Host "Current container status..."
docker compose ps
