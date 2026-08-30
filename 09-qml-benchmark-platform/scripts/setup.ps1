$ErrorActionPreference = "Stop"

Set-Location (Split-Path -Parent $PSScriptRoot)

docker version | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop with the Linux engine is required."
}

docker build --file deployment/quality-gate.Dockerfile --tag qml-benchmark-quality-gate:s2 .
if ($LASTEXITCODE -ne 0) {
    throw "Sprint 2 dependency image build failed."
}

Write-Host "OK - Project 09 Sprint 2 dependencies are ready"
