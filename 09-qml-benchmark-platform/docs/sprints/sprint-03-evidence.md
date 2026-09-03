# Sprint 3 evidence — Quantum Noise Limitations Board

## Implemented evidence path

1. Load the immutable Sprint 1 dataset snapshot and train-only preprocessing.
2. Build the Sprint 2 fidelity kernel over fixed train and validation sample order.
3. Execute ideal, finite-shot, noisy and readout-mitigated modes with paired seeds.
4. Train and evaluate the same precomputed-kernel QSVM for every mode.
5. Persist the report and expose JSON, CSV and HTML representations.
6. Render uncertainty, mitigation, resources, trainability proxy and traceable findings in Dash.

## External evidence boundary

- Project 52 is represented by a reviewed digest pointer to its sealed final bundle: 30 cases,
  150 runs, zero failed runs and zero hardware jobs.
- Project 53 contained only a README at review time. It is recorded as conceptual-only and is not
  loaded by the API as verified executable evidence.

## Claims and limitations

- No quantum hardware is used.
- The declared channel supports sensitivity analysis, not device realism.
- Readout inversion is mitigation, not quantum error correction.
- At most four seeds and a small synthetic dataset provide descriptive evidence only.
- The trainability signal neither proves nor excludes a barren plateau.
- No result establishes quantum advantage or a universal model ranking.

## Acceptance

The sprint is complete only after `scripts/run-quality-gate.ps1` prints:

```text
OK - Project 09 Sprint 3 quality gate passed
```

Until that line is observed, the status remains release candidate rather than verified release.
