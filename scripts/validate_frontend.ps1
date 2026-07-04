Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "=============================="
Write-Host "Validating frontend"
Write-Host "=============================="

Write-Host "Running frontend lint..."
docker compose exec frontend npm run lint

Write-Host "Running frontend typecheck..."
docker compose exec frontend npm run typecheck

Write-Host "Running frontend build..."
docker compose exec frontend npm run build
