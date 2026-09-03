# ADR 0003 — Paired bounded noise evidence

## Status

Accepted for Sprint 3.

## Decision

The platform compares one quantum fidelity kernel and one QSVM across four modes: ideal,
finite-shot, declared noisy, and readout-mitigated. Every mode preserves the dataset snapshot,
train/validation split, model, seed and bounded execution budget.

The local noise profile mixes the ideal kernel probability with a bounded depolarizing channel,
then applies a symmetric readout channel before deterministic binomial sampling. Mitigation only
inverts the declared symmetric readout channel. It does not correct depolarization and is not
quantum error correction.

## Consequences

- Paired deltas are traceable to one comparison identity.
- Runtime, shots, depth, calibration and uncertainty remain visible.
- The trainability view is explicitly a diagnostic proxy and cannot establish a barren plateau.
- Arbitrary code, QASM, notebooks, plugins and remote quantum jobs remain outside the API.
- No output may be interpreted as quantum advantage or hardware characterization.
