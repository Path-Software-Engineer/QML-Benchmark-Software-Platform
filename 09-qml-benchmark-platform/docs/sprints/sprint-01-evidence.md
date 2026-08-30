# Sprint 1 — Quantum Data Encoding Visualizer

## Delivered scope

- versioned synthetic dataset fixture, manifest and canonical content hash;
- deterministic stratified train/validation/test membership with no overlap;
- `StandardScaler` fitted only on train and applied unchanged to other splits;
- basis, angle and amplitude mathematical reference encodings;
- real Qiskit Statevector and PennyLane `default.qubit` adapter evidence;
- visible qubits, depth, feature count, padding, normalization and warnings;
- PostgreSQL-backed snapshot and preview persistence;
- FastAPI OpenAPI/Swagger surface and canonical evidence bundle export;
- responsive Dash explorer with chart and equivalent accessible tables;
- containerized lint, type, unit, contract and cross-layer acceptance gate.

## Evidence boundary

This sprint demonstrates data preparation and state encoding only. The included data is a
repository-owned synthetic fixture. Results are not evidence of predictive performance,
quantum hardware behavior, a production QML workload or quantum advantage.

## Acceptance command

```powershell
Set-Location "C:\JeanLoa\Path-Software-Engineer\QML-Benchmark-Software-Platform\09-qml-benchmark-platform"
.\scripts\run-quality-gate.ps1
```

Expected terminal condition:

```text
OK - Project 09 Sprint 1 quality gate passed
```
