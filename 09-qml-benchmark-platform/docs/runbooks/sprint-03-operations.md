# Sprint 3 operations runbook

## Validate

```powershell
Set-Location "C:\JeanLoa\Path-Software-Engineer\QML-Benchmark-Software-Platform\09-qml-benchmark-platform"
.\scripts\setup.ps1
.\scripts\run-quality-gate.ps1
```

The gate builds pinned dependencies, runs lint, formatting, typing and tests, validates production
images, migrates PostgreSQL, performs the cross-layer smoke flow and tears the stack down.

## Inspect manually

```powershell
docker compose up --detach --build --wait
```

- Dashboard: `http://127.0.0.1:8050`
- Swagger: `http://127.0.0.1:8080/docs`
- Readiness: `http://127.0.0.1:8080/health/ready`

## Stop and recover

```powershell
docker compose down --remove-orphans
```

If migration `0003_sprint_03_noise_limitations` fails, stop the stack and inspect PostgreSQL logs.
Do not delete the volume or rewrite an applied migration. Fix forward with a new migration.

## Rollback

Run the Sprint 2 Git tag and its matching images. The new table is additive, so Sprint 2 ignores it.
Do not drop evidence tables during rollback.

## Azure preflight and release

Run the non-mutating preflight first:

```powershell
.\scripts\deploy-azure.ps1
```

The apply path requires a clean worktree tagged `v1.0.0-qml-benchmark-platform`, plus
`GHCR_USERNAME` and a process-scoped `GHCR_TOKEN`. It publishes immutable images only after the
full quality gate and Azure validation pass.

The recruiter deployment uses the shared Container Apps Consumption environment, scales from zero
to one replica, and uses memory persistence. Reports reset on scale-down or revision replacement.
