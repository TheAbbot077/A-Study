Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Write-Host "=============================="
Write-Host "Running full validation"
Write-Host "=============================="

& "$PSScriptRoot/validate_backend.ps1"
& "$PSScriptRoot/validate_frontend.ps1"
