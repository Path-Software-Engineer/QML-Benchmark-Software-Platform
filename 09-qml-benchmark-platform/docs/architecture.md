# QML benchmark platform architecture

```text
Versioned CSV + manifest
          |
          v
qml_core: split -> train-only scaler -> basis / angle / amplitude
          |                         | Qiskit + PennyLane cross-check
          v
FastAPI contracts -> PostgreSQL evidence repository -> SHA-256 export
          |
          v HTTP only
Dash controls -> resource cards -> circuit table -> statevector chart + table
```

## Runtime services

| Service | Responsibility | Port |
|---|---|---:|
| `postgres` | Dataset snapshots and encoding previews | internal |
| `benchmark-api` | QML execution, persistence, OpenAPI and exports | 8080 |
| `dashboard` | Accessible evidence exploration over HTTP | 8050 |

The local Compose profile is the Sprint 1 acceptance environment. No quantum account,
token, remote simulator or hardware queue is necessary.

## Sprint 2 benchmark vertical

```text
EvaluationProtocol + DatasetSnapshot
                 |
                 v
linear / polynomial / RBF / angle-fidelity matrices
                 | sample order + symmetry + SHA-256
                 v
logistic / RBF-SVM / precomputed QSVM / bounded VQC
                 | paired seeds + common metrics + resources
                 v
PostgreSQL BenchmarkReport -> JSON / CSV / HTML
                 |
                 v HTTP only
Dash heatmap + matrix table + variability + resource board
```

The `migrate` service applies every idempotent migration before FastAPI starts, including when the
Sprint 1 PostgreSQL volume already exists. Verified P50/P51 evidence enters through a separate
data-only importer; it never adds executable code to the runtime.

## Sprint 3 limitations vertical

```text
NoiseProtocol + fixed Sprint 2 fidelity kernel
                 |
                 v
ideal / finite-shot / noisy / readout-mitigated execution
                 | paired dataset + split + model + seeds + budget
                 v
QSVM metrics + uncertainty + runtime + calibration + depth proxy
                 |
                 v
PostgreSQL NoiseLimitationsReport -> JSON / CSV / HTML
                 |
                 v HTTP only
Dash quality + mitigation + resource + trainability + findings board
```

The profile registry and request bounds prevent arbitrary execution. Project 52 contributes a
digest-verified data pointer. Project 53 is recorded as conceptual-only because no sealed evidence
bundle was available; it is not loaded into the runtime evidence registry.
