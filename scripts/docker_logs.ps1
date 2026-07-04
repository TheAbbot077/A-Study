Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$services = @("backend", "celery", "frontend", "postgres", "redis")

foreach ($service in $services) {
    Write-Host "=============================="
    Write-Host "Logs for $service"
    Write-Host "=============================="
    docker compose logs --tail=100 $service
}
