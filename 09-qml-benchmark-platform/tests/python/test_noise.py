from __future__ import annotations

from qml_core.datasets import prepare_dataset
from qml_core.noise import run_noise_limitations
from qml_core.noise_models import NoiseProtocol
from tests.python.conftest import ROOT


def test_noise_study_is_paired_bounded_and_traceable() -> None:
    prepared = prepare_dataset(
        ROOT / "data/datasets/qml_encoding_demo_v1.csv",
        ROOT / "data/datasets/qml_encoding_demo_v1.manifest.json",
    )
    protocol = NoiseProtocol(
        seeds=(3501, 3502),
        shots=64,
        noise_strength=0.08,
        readout_error=0.04,
        max_depth=2,
    )
    report = run_noise_limitations(prepared, protocol)
    assert {profile.execution_mode for profile in report.profiles} == {
        "ideal",
        "shot-based",
        "noisy",
        "mitigated",
    }
    assert len(report.runs) == 8
    assert all(run.comparison_id == report.comparison_id for run in report.runs)
    assert all(run.train_sample_ids == prepared.snapshot.split.train_ids for run in report.runs)
    assert all(
        run.evaluation_sample_ids == prepared.snapshot.split.validation_ids for run in report.runs
    )
    assert all(run.resources["hardware_jobs"] == 0 for run in report.runs)
    assert all(run.kernel_symmetry_error == 0 for run in report.runs)
    assert any(
        run.metrics["kernel_mae_from_ideal"] > 0
        for run in report.runs
        if run.profile.execution_mode == "noisy"
    )
    assert len(report.findings) == 4
    assert report.provenance["quantum_advantage_claimed"] is False
    assert report.provenance["error_correction_claimed"] is False


def test_noise_protocol_rejects_unbounded_requests() -> None:
    for protocol in (
        NoiseProtocol(shots=4096),
        NoiseProtocol(noise_strength=0.5),
        NoiseProtocol(readout_error=0.2),
        NoiseProtocol(max_depth=9),
        NoiseProtocol(seeds=(1, 1)),
    ):
        try:
            protocol.validate()
        except ValueError:
            continue
        raise AssertionError("unbounded noise protocol was accepted")


def test_readout_mitigation_is_explicitly_scoped() -> None:
    prepared = prepare_dataset(
        ROOT / "data/datasets/qml_encoding_demo_v1.csv",
        ROOT / "data/datasets/qml_encoding_demo_v1.manifest.json",
    )
    report = run_noise_limitations(
        prepared,
        NoiseProtocol(seeds=(3501,), shots=64, max_depth=1),
    )
    mitigated = next(run for run in report.runs if run.profile.execution_mode == "mitigated")
    assert mitigated.calibration is not None
    assert mitigated.calibration["scope"] == "symmetric readout channel only"
    assert "does not correct depolarization" in report.mitigation.applicability
