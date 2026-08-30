$ErrorActionPreference = "Stop"

Set-Location (Split-Path -Parent $PSScriptRoot)

function Invoke-Checked {
    param([string]$Label, [scriptblock]$Action)
    Write-Host "  -> $Label"
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed."
    }
}

Write-Host "[1/7] Validating versioned Sprint 2 release assets"
Invoke-Checked "Contracts, boundaries and repository artifacts" {
    docker run --rm --volume "${PWD}:/workspace" --workdir /workspace `
        python:3.12.11-slim-bookworm sh -c `
        "pip install --quiet jsonschema==4.25.1 && python scripts/validate-release.py && python scripts/validate-repository.py"
}

Write-Host "[2/7] Building the pinned quality image"
Invoke-Checked "Python 3.12 dependency and test image" {
    docker build --file deployment/quality-gate.Dockerfile `
        --tag qml-benchmark-quality-gate:s2 .
}

Write-Host "[3/7] Running lint, format, typing and tests"
Invoke-Checked "Ruff, mypy and pytest" {
    docker run --rm qml-benchmark-quality-gate:s2
}

Write-Host "[4/7] Validating Compose and production images"
Invoke-Checked "Docker Compose model" { docker compose config --quiet }
Invoke-Checked "FastAPI runtime image" {
    docker compose build benchmark-api
}
Invoke-Checked "Dash runtime image" {
    docker compose build dashboard
}

Write-Host "[5/7] Starting PostgreSQL, FastAPI and Dash"
try {
    Invoke-Checked "Healthy local platform" {
        docker compose up --detach --wait --wait-timeout 240
    }

    Write-Host "[6/7] Running real cross-layer acceptance"
    Invoke-Checked "Snapshot, encoding adapters, persistence, export and UI" {
        docker run --rm --network qml-benchmark-platform_default `
            --env API_URL=http://benchmark-api:8080 `
            --env DASHBOARD_URL=http://dashboard:8050 `
            --volume "${PWD}:/workspace:ro" --workdir /workspace `
            python:3.12.11-slim-bookworm python scripts/smoke-test.py
    }

    Write-Host "[7/7] Checking repository hygiene"
    Invoke-Checked "Git whitespace" { git diff --check -- . }
    Invoke-Checked "Repository content recheck" {
        docker run --rm --volume "${PWD}:/workspace" --workdir /workspace `
            qml-benchmark-quality-gate:s2 sh -c `
            "python scripts/validate-release.py && python scripts/validate-repository.py"
    }

    Write-Host "OK - Project 09 Sprint 2 quality gate passed"
}
finally {
    docker compose down --remove-orphans
}
