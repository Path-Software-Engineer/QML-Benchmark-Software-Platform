# ADR 0002: Fair, bounded QML comparison protocol

- Status: Accepted
- Date: 2026-08-29

## Context

Sprint 2 compares quantum and classical kernels plus QSVM, VQC and classical models. A result is
misleading if models use different data, preprocessing, splits, seeds, budgets or metrics. Large
circuits, arbitrary imports and unconstrained tuning are outside the portfolio runtime boundary.

## Decision

All runs share one immutable `DatasetSnapshot` and versioned `EvaluationProtocol`. The protocol
binds the validation split, one to three unique seeds, at most twenty samples, three features and
no more than eight VQC iterations. Each model has one declared configuration; no hidden grid search
is performed.

The classical registry contains linear, polynomial and RBF kernels. The quantum kernel is the
squared state overlap of an allowlisted angle-RY feature map on a local statevector backend. QSVM
uses the precomputed quantum kernel. VQC uses an angle embedding, a bounded RY ansatz, nearest-wire
entanglement and deterministic finite-difference optimization. Logistic regression and RBF SVM are
required controls.

Every square matrix binds ordered sample ids, shape, dtype, symmetry error and SHA-256. Reports
retain per-seed metrics, confusion matrices, resources, distributions, provenance and limitations.
Wall-clock time always includes its environment and measurement method.

External P50/P51 evidence is data-only. Imports accept allowlisted schemas, verified/sealed status,
SHA-256 identities and no executable fields. Repeated imports return the same identity.

## Consequences

- Comparisons are paired and reproducible within the bounded local environment.
- Runtime and model metrics are visible with seed variation rather than a single accuracy number.
- The product can inspect upstream evidence without mixing repositories or accepting code.
- Results remain demonstrations on a tiny synthetic dataset, not claims of hardware behavior,
  universal model superiority or quantum advantage.
