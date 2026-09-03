# Sprint 3 threat model

## Protected assets

- immutable dataset and split identity;
- paired comparison and kernel checksums;
- persisted report provenance;
- evidence allowlist and upstream digests;
- bounded CPU, memory and request duration.

## Threats and controls

| Threat | Control |
|---|---|
| Arbitrary quantum or Python execution | Typed request fields only; no code, QASM, notebook, pickle, plugin or remote job inputs |
| Resource exhaustion | One to four unique seeds, 64–2048 shots and depth 1–8 |
| Misleading comparison | Dataset, split, model, seeds and budget are bound to one comparison ID |
| Evidence substitution | Reviewed project allowlist plus exact manifest and summary SHA-256 values |
| Stored or reflected markup | Generated HTML escapes report-controlled strings; requests cannot supply markup fields |
| Overclaiming mitigation | Contract and UI state that readout inversion is not error correction |
| Statistical overclaiming | Descriptive intervals, visible sample count and explicit small-sample caveat |

The service uses no quantum credentials, remote hardware jobs or user-supplied executable content.
