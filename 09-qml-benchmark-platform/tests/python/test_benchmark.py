from __future__ import annotations

from qml_core.benchmark import run_benchmark
from qml_core.benchmark_models import EvaluationProtocol
from qml_core.datasets import prepare_dataset
from tests.python.conftest import ROOT


def test_bounded_paired_benchmark_preserves_protocol_and_claim_boundary() -> None:
    prepared = prepare_dataset(
        ROOT / "data/datasets/qml_encoding_demo_v1.csv",
        ROOT / "data/datasets/qml_encoding_demo_v1.manifest.json",
    )
    protocol = EvaluationProtocol(seeds=(2409,), repetitions=1, max_vqc_iterations=1)
    report = run_benchmark(prepared, protocol)
    assert len(report.kernel_matrices) == 4
    assert len(report.runs) == 4
    assert {run.model.kind for run in report.runs} == {"logistic", "rbf-svm", "qsvm", "vqc"}
    assert all(run.plan_id == report.plan_id for run in report.runs)
    assert all(run.split == "validation" for run in report.runs)
    assert all(run.train_sample_ids == prepared.snapshot.split.train_ids for run in report.runs)
    assert all(
        run.evaluation_sample_ids == prepared.snapshot.split.validation_ids for run in report.runs
    )
    assert all(0.0 <= float(run.metrics["f1"]) <= 1.0 for run in report.runs)
    assert report.provenance["quantum_advantage_claimed"] is False
    assert report.provenance["hardware_jobs"] == 0
    assert all(matrix.symmetric for matrix in report.kernel_matrices)
