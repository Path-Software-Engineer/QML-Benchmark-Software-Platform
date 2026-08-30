# Sprint 2 — Quantum Kernel Results Visualizer

## Delivered scope

- versioned `EvaluationProtocol`, `KernelSpec`, `ModelSpec` and report contracts;
- linear, degree-two polynomial, RBF and angle-fidelity quantum kernels;
- matrices with ordered sample ids, shape, dtype, symmetry checks and SHA-256;
- precomputed-kernel QSVM, bounded statevector VQC, logistic and RBF-SVM controls;
- paired seeds, shared snapshot/split/preprocessing and one configuration per model;
- accuracy, precision, recall, F1, ROC-AUC, confusion matrices and variability summaries;
- runtime, qubits, depth, shots, parameters and circuit-evaluation accounting;
- PostgreSQL persistence and JSON, CSV and HTML report surfaces;
- idempotent, data-only evidence pointers for verified P50 and P51 final bundles;
- Dash heatmap, equivalent matrix table, quality/error bars, resources and claim boundary;
- unit, contract, API, persistence and real cross-layer smoke acceptance.

## Verified upstream provenance

| Project | Manifest SHA-256 | Summary SHA-256 | State |
|---|---|---|---|
| P50 quantum-kernel-benchmark | `d2b19f60d6c51fec536c6ae414be34e4ec9ddb5d8ecd51c761bb4ff01919cbdb` | `12069310519791a94e8a84b327f9a55653ddb071c725c623270e09912060d938` | verified, sealed, zero hardware |
| P51 vqc-qsvm-comparison-suite | `1539a588c94943d74aab4fe8b75eb912196c2518012f9cfa237a4cfbeb10fcdf` | `879770cfd5ef494bab1f85cc5e22ea191b6208fbb953fc1aaa60768a3af46080` | verified, sealed, zero hardware |

The repository stores compact data-only pointers, not upstream notebooks, Python environments or
large raw result files.

## Threats to validity

| Threat | Control | Residual limitation |
|---|---|---|
| Leakage | Immutable split and train-only scaler | One synthetic dataset |
| Unfair comparison | Shared protocol, seeds and metrics | Different model inductive biases remain |
| Matrix/order drift | Sample ids, shape, symmetry and checksum | Local floating-point backend |
| Seed variation | Paired repetitions and distributions | At most three seeds |
| Runtime distortion | Same container plus environment/method labels | Wall-clock remains host-dependent |
| Overclaiming | Mandatory limitation text and false advantage flag | Does not establish external validity |

## Acceptance

```powershell
Set-Location "C:\JeanLoa\Path-Software-Engineer\QML-Benchmark-Software-Platform\09-qml-benchmark-platform"
.\scripts\run-quality-gate.ps1
```

Expected terminal condition:

```text
OK - Project 09 Sprint 2 quality gate passed
```
