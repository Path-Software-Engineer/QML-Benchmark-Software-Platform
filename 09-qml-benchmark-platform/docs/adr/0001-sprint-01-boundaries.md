# ADR 0001: Sprint 1 execution and boundary model

- Status: Accepted
- Date: 2026-08-26

## Context

The first increment must explain quantum data encoding without mixing UI concerns,
database access, or unsupported claims. It also has to run reproducibly without quantum
hardware.

## Decision

The platform uses three explicit boundaries:

1. `qml_core` owns validation, mathematical reference encodings and allowlisted Qiskit and
   PennyLane statevector adapters.
2. FastAPI owns execution, versioned contracts, provenance and PostgreSQL persistence.
3. Dash is an HTTP client. It neither imports QML libraries nor opens database connections.

Every preview is derived from an executed encoding artifact. The API persists the exact
artifact and exports a canonical SHA-256 evidence bundle. Dataset preprocessing uses a
versioned deterministic split and fits `StandardScaler` exclusively on training rows.

## Consequences

- The dashboard cannot silently diverge from API evidence.
- The reference backend and two framework adapters can be cross-checked.
- Statevector simulation is deterministic and hardware-independent.
- Basis encoding rejects non-binary values instead of hiding a discretization policy.
- Angle clipping and amplitude state-preparation cost remain visible limitations.
- Sprint 1 does not execute kernels, train classifiers or claim quantum advantage.
