from __future__ import annotations

import json

import numpy as np
import pytest

from qml_core.benchmark_models import EvaluationProtocol
from qml_core.evidence import validate_evidence_bundle
from qml_core.kernels import compute_kernel, get_kernel, matrix_artifact
from tests.python.conftest import ROOT


def test_classical_kernels_match_known_formulas() -> None:
    values = np.asarray([[1.0, 0.0], [0.0, 1.0]])
    assert np.allclose(compute_kernel(get_kernel("linear-v1"), values), np.eye(2))
    polynomial = compute_kernel(get_kernel("polynomial-d2-v1"), values)
    assert np.allclose(polynomial, [[2.25, 1.0], [1.0, 2.25]])
    rbf = compute_kernel(get_kernel("rbf-gamma05-v1"), values)
    assert np.allclose(np.diag(rbf), 1.0)
    assert np.all(rbf <= 1.0)


def test_quantum_fidelity_matrix_is_symmetric_with_unit_diagonal() -> None:
    values = np.asarray([[-0.5, 0.2], [0.4, -0.1], [0.8, 0.7]])
    matrix = compute_kernel(get_kernel("fidelity-angle-ry-v1"), values)
    assert np.allclose(matrix, matrix.T)
    assert np.allclose(np.diag(matrix), 1.0)
    assert np.all((matrix >= 0.0) & (matrix <= 1.0 + 1e-12))


def test_matrix_artifact_binds_sample_order_and_checksum() -> None:
    values = np.asarray([[0.0, 1.0], [1.0, 0.0]])
    kernel = get_kernel("linear-v1")
    first = matrix_artifact(kernel, values, ["sample-a", "sample-b"])
    second = matrix_artifact(kernel, values, ["sample-b", "sample-a"])
    assert first.shape == (2, 2)
    assert first.symmetric is True
    assert first.sample_ids == ("sample-a", "sample-b")
    assert first.projection_method == "centered-kernel-pca"
    assert len(first.projection) == 2
    assert first.checksum != second.checksum


def test_protocol_rejects_unbounded_or_unpaired_configuration() -> None:
    with pytest.raises(ValueError, match="repetitions"):
        EvaluationProtocol(seeds=(1, 2), repetitions=1).validate()
    with pytest.raises(ValueError, match="budget"):
        EvaluationProtocol(max_samples=33).validate()


@pytest.mark.parametrize(
    "filename",
    ["p50-kernel-benchmark.pointer.json", "p51-vqc-qsvm-comparison.pointer.json"],
)
def test_sealed_ai_evidence_pointers_are_accepted_idempotently(filename: str) -> None:
    bundle = json.loads((ROOT / "data/evidence" / filename).read_text(encoding="utf-8"))
    first = validate_evidence_bundle(bundle)
    second = validate_evidence_bundle(bundle)
    assert first == second
    assert first["status"] == "accepted"
    assert first["bundle_sha256"] != first["source_summary_sha256"]


def test_evidence_import_rejects_executable_or_advantage_claims() -> None:
    bundle = json.loads(
        (ROOT / "data/evidence/p50-kernel-benchmark.pointer.json").read_text(encoding="utf-8")
    )
    bundle["quantum_advantage_claimed"] = True
    with pytest.raises(ValueError, match="quantum advantage"):
        validate_evidence_bundle(bundle)
    bundle["quantum_advantage_claimed"] = False
    bundle["summary"]["python"] = "print('untrusted')"
    with pytest.raises(ValueError, match="executable"):
        validate_evidence_bundle(bundle)


def test_evidence_import_rejects_tampered_reviewed_summary() -> None:
    bundle = json.loads(
        (ROOT / "data/evidence/p51-vqc-qsvm-comparison.pointer.json").read_text(encoding="utf-8")
    )
    bundle["summary"]["validation_run_count"] = 41
    with pytest.raises(ValueError, match="identity mismatch"):
        validate_evidence_bundle(bundle)
