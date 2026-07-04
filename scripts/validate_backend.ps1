Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "=============================="
Write-Host "Validating backend"
Write-Host "=============================="

Write-Host "Running Django system checks..."
docker compose exec backend python manage.py check

Write-Host "Running migration check..."
docker compose exec backend python manage.py makemigrations --check --dry-run

Write-Host "Running backend tests..."
docker compose exec backend pytest
