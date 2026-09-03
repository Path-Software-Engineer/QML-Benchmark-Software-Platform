from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(source: str, fragment: str, message: str) -> None:
    if fragment not in source:
        raise SystemExit(message)


def reject(source: str, fragment: str, message: str) -> None:
    if re.search(re.escape(fragment), source, re.IGNORECASE):
        raise SystemExit(message)


def main() -> None:
    main_bicep = (ROOT / "infra/azure/main.bicep").read_text(encoding="utf-8")
    workload = (ROOT / "infra/azure/workload.bicep").read_text(encoding="utf-8")
    caddy = (ROOT / "infra/azure/Caddyfile").read_text(encoding="utf-8")
    deploy = (ROOT / "scripts/deploy-azure.ps1").read_text(encoding="utf-8")
    combined = "\n".join((main_bicep, workload, deploy))

    for forbidden in (
        "Microsoft.ContainerRegistry",
        "Microsoft.OperationalInsights",
        "Microsoft.Storage",
        "Microsoft.DBforPostgreSQL",
        "Microsoft.Sql",
        "Microsoft.Cache",
    ):
        reject(combined, forbidden, f"fixed-cost Azure resource is forbidden: {forbidden}")

    require(workload, "minReplicas: 0", "Container Apps must scale to zero")
    require(workload, "maxReplicas: 1", "the recruiter demo must cap replicas at one")
    require(
        main_bicep,
        "param existingEnvironmentResourceId string = ''",
        "regional environment reuse must be configurable",
    )
    require(
        workload,
        "if (empty(existingEnvironmentResourceId))",
        "new environment creation must remain conditional",
    )
    require(workload, "@secure()\nparam registryPassword", "registry token must be secure")
    for container in ("gateway", "api", "dashboard"):
        require(workload, f"name: '{container}'", f"{container} container is missing")
    reject(combined, "storageType:", "cloud recruiter demo must not provision a storage volume")
    reject(combined, "DATABASE_URL", "cloud demo must not require a paid database")
    reject(main_bicep, "output registryPassword", "registry token must never be an output")

    for route in ("/api/*", "/health/*", "/docs", "/openapi.json"):
        require(caddy, route, f"same-origin gateway route is missing: {route}")
    require(caddy, "127.0.0.1:8080", "gateway must reach the API sidecar")
    require(caddy, "127.0.0.1:8050", "gateway must reach the dashboard sidecar")

    require(deploy, "[switch]$Apply", "deployment must be approval gated")
    require(
        deploy,
        "[switch]$AllowCreateEnvironment",
        "new environment creation must be separately approval gated",
    )
    require(deploy, "if (-not $Apply)", "deployment must default to preflight only")
    require(deploy, "$env:GHCR_TOKEN", "GHCR token must come from process environment")
    require(deploy, "docker push", "immutable release images must be published")
    require(deploy, "az deployment sub what-if", "Azure what-if is required")
    require(
        deploy,
        "providers/Microsoft.App/managedEnvironments?api-version=2025-07-01",
        "subscription-wide environment inventory is required",
    )
    require(
        deploy,
        "git describe --exact-match --tags HEAD",
        "apply must require a release tag",
    )
    if deploy.index("Azure deployment validation before image publication") > deploy.index(
        "docker push"
    ):
        raise SystemExit("Azure validation must run before registry publication")
    for evidence in (
        "/health/ready",
        "/_dash-layout",
        "/docs",
        "/openapi.json",
        "/api/v1/noise/reports",
    ):
        require(deploy, evidence, f"live acceptance evidence is missing: {evidence}")
    reject(deploy, "az acr build", "ACR Tasks are outside the zero-fixed-cost design")

    print("OK - Azure scale-to-zero QML release contract is structurally complete")


if __name__ == "__main__":
    main()
