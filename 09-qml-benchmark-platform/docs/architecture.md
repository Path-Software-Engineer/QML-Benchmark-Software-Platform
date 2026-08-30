# Sprint 1 architecture

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
