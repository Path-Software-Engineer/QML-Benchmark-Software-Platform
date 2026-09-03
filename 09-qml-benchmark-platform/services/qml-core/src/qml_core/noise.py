from __future__ import annotations

import hashlib
import json
import math
import time
from collections.abc import Sequence
from dataclasses import replace
from typing import Any

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.svm import SVC

from qml_core.datasets import PreparedDataset
from qml_core.kernels import compute_kernel, get_kernel
from qml_core.noise_models import (
    LimitationFinding,
    MitigationSpec,
    NoiseLimitationsReport,
    NoiseProfile,
    NoiseProtocol,
    NoiseRun,
)


def mitigation_registry() -> tuple[MitigationSpec, ...]:
    return (
        MitigationSpec(
            schema_version="qml.mitigation-spec.v1",
            mitigation_id="symmetric-readout-inversion-v1",
            method="symmetric-readout-inversion",
            calibration_shots=512,
            regularization=1e-6,
            applicability=(
                "Corrects the declared symmetric readout channel only; it does not correct "
                "depolarization, model error, decoherence, or training instability."
            ),
        ),
    )


def noise_profile_registry(protocol: NoiseProtocol | None = None) -> tuple[NoiseProfile, ...]:
    current = protocol or NoiseProtocol()
    current.validate()
    mitigation = mitigation_registry()[0]
    profiles = (
        NoiseProfile(
            "qml.noise-profile.v1",
            "ideal-statevector-v1",
            "ideal",
            "numpy-statevector",
            0,
            0.0,
            0.0,
            None,
        ),
        NoiseProfile(
            "qml.noise-profile.v1",
            "shot-only-v1",
            "shot-based",
            "numpy-binomial",
            current.shots,
            0.0,
            0.0,
            None,
        ),
        NoiseProfile(
            "qml.noise-profile.v1",
            "depolarizing-readout-v1",
            "noisy",
            "numpy-channel-simulator",
            current.shots,
            current.noise_strength,
            current.readout_error,
            None,
        ),
        NoiseProfile(
            "qml.noise-profile.v1",
            "readout-mitigated-v1",
            "mitigated",
            "numpy-channel-simulator",
            current.shots,
            current.noise_strength,
            current.readout_error,
            mitigation.mitigation_id,
        ),
    )
    for profile in profiles:
        profile.validate()
    mitigation.validate()
    return profiles


def _partition(
    prepared: PreparedDataset,
    identifiers: tuple[str, ...],
) -> tuple[np.ndarray, np.ndarray]:
    frame = prepared.transformed.set_index("sample_id").loc[list(identifiers)]
    values = frame[list(prepared.snapshot.feature_names)].to_numpy(dtype=float)
    classes = sorted(prepared.raw[prepared.snapshot.target_name].astype(str).unique())
    if len(classes) != 2:
        raise ValueError("noise benchmark requires exactly two target classes")
    mapping = {label: index for index, label in enumerate(classes)}
    labels = frame[prepared.snapshot.target_name].astype(str).map(mapping).to_numpy(dtype=int)
    return values, labels


def _observed_probability(value: float, profile: NoiseProfile) -> float:
    probability = float(value)
    if profile.execution_mode in {"noisy", "mitigated"}:
        probability = (1.0 - profile.depolarizing_strength) * probability
        probability += profile.depolarizing_strength * 0.5
        probability = (1.0 - profile.readout_error) * probability + profile.readout_error * (
            1.0 - probability
        )
    return float(np.clip(probability, 0.0, 1.0))


def _mitigate_probability(value: float, profile: NoiseProfile, regularization: float) -> float:
    denominator = max(1.0 - 2.0 * profile.readout_error, regularization)
    return float(np.clip((value - profile.readout_error) / denominator, 0.0, 1.0))


def _execute_kernel(
    ideal: np.ndarray,
    profile: NoiseProfile,
    seed: int,
    mitigation: MitigationSpec,
) -> np.ndarray:
    if profile.execution_mode == "ideal":
        return ideal.copy()
    generator = np.random.default_rng(seed)
    result = np.empty_like(ideal, dtype=float)
    square = ideal.shape[0] == ideal.shape[1] and np.allclose(ideal, ideal.T)
    for row in range(ideal.shape[0]):
        start = row if square else 0
        for column in range(start, ideal.shape[1]):
            probability = _observed_probability(float(ideal[row, column]), profile)
            sampled = float(generator.binomial(profile.shots, probability) / profile.shots)
            if profile.execution_mode == "mitigated":
                sampled = _mitigate_probability(sampled, profile, mitigation.regularization)
            result[row, column] = sampled
            if square:
                result[column, row] = sampled
    return result


def _metrics(
    labels: np.ndarray,
    predictions: np.ndarray,
    scores: np.ndarray,
) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(labels, predictions)),
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "f1": float(f1_score(labels, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(labels, scores)),
    }


def _checksum(profile: NoiseProfile, sample_ids: Sequence[str], matrix: np.ndarray) -> str:
    canonical = json.dumps(
        {
            "profile": profile.as_dict(),
            "sample_ids": list(sample_ids),
            "values": np.round(matrix, 12).tolist(),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _calibration_manifest(
    profile: NoiseProfile,
    mitigation: MitigationSpec,
) -> dict[str, Any] | None:
    if profile.execution_mode != "mitigated":
        return None
    error = profile.readout_error
    matrix = ((1.0 - error, error), (error, 1.0 - error))
    canonical = json.dumps(matrix, separators=(",", ":"))
    return {
        "schema_version": "qml.calibration-manifest.v1",
        "mitigation_id": mitigation.mitigation_id,
        "shots": mitigation.calibration_shots,
        "confusion_matrix": matrix,
        "determinant": 1.0 - 2.0 * error,
        "sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "scope": "symmetric readout channel only",
    }


def _uncertainty(runs: Sequence[NoiseRun]) -> tuple[dict[str, Any], ...]:
    summaries: list[dict[str, Any]] = []
    for mode in ("ideal", "shot-based", "noisy", "mitigated"):
        selected = [run for run in runs if run.profile.execution_mode == mode]
        for metric in ("accuracy", "f1", "roc_auc", "kernel_mae_from_ideal"):
            values = np.asarray([run.metrics[metric] for run in selected], dtype=float)
            mean = float(np.mean(values))
            std = float(np.std(values, ddof=1)) if len(values) > 1 else 0.0
            margin = 1.96 * std / math.sqrt(len(values)) if len(values) > 1 else 0.0
            summaries.append(
                {
                    "execution_mode": mode,
                    "metric": metric,
                    "n": len(values),
                    "mean": mean,
                    "standard_deviation": std,
                    "interval_low": max(0.0, mean - margin),
                    "interval_high": min(1.0, mean + margin),
                    "interval_method": "normal approximation; descriptive only",
                    "minimum": float(np.min(values)),
                    "maximum": float(np.max(values)),
                }
            )
    return tuple(summaries)


def _trainability(protocol: NoiseProtocol) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    for depth in range(1, protocol.max_depth + 1):
        norms: list[float] = []
        for seed in protocol.seeds:
            generator = np.random.default_rng(seed + depth * 101)
            angles = generator.uniform(-math.pi, math.pi, size=depth)
            gradient = np.asarray(
                [
                    -math.sin(float(angles[index]))
                    * float(np.prod(np.delete(np.cos(angles), index)))
                    for index in range(depth)
                ]
            )
            attenuation = (1.0 - protocol.noise_strength) ** depth
            attenuation *= 1.0 - 2.0 * protocol.readout_error
            sampled = gradient * attenuation
            sampled += generator.normal(0.0, 1.0 / math.sqrt(protocol.shots), size=depth)
            norms.append(float(np.linalg.norm(sampled)))
        rows.append(
            {
                "signal_id": f"trainability-depth-{depth}",
                "method": "analytic product-cosine gradient proxy with sampled noise",
                "depth": depth,
                "n": len(norms),
                "gradient_norm_mean": float(np.mean(norms)),
                "gradient_norm_variance": float(np.var(norms)),
                "near_zero_fraction": float(np.mean(np.asarray(norms) < 1e-3)),
                "claim_boundary": (
                    "Diagnostic proxy only; it does not establish or exclude a barren plateau."
                ),
            }
        )
    return tuple(rows)


def _findings(
    runs: Sequence[NoiseRun],
    uncertainty: Sequence[dict[str, Any]],
    trainability: Sequence[dict[str, Any]],
) -> tuple[LimitationFinding, ...]:
    mean_f1 = {
        str(item["execution_mode"]): float(item["mean"])
        for item in uncertainty
        if item["metric"] == "f1"
    }
    mean_kernel_error = {
        str(item["execution_mode"]): float(item["mean"])
        for item in uncertainty
        if item["metric"] == "kernel_mae_from_ideal"
    }
    shot_std = next(
        float(item["standard_deviation"])
        for item in uncertainty
        if item["execution_mode"] == "shot-based" and item["metric"] == "f1"
    )
    noisy_delta = mean_f1["noisy"] - mean_f1["ideal"]
    mitigation_delta = mean_f1["mitigated"] - mean_f1["noisy"]
    noisy_kernel_error = mean_kernel_error["noisy"]
    deepest = trainability[-1]
    return (
        LimitationFinding(
            "qml.limitation-finding.v1",
            "finding-shot-variability",
            "medium" if shot_std > 0.02 else "low",
            "sampling",
            "Finite-shot estimates vary across paired seeds",
            f"Observed shot-based F1 standard deviation: {shot_std:.4f}.",
            tuple(run.run_id for run in runs if run.profile.execution_mode == "shot-based"),
            ("Three or fewer local seeds are descriptive, not population-level inference.",),
            "observed" if shot_std > 0 else "not-observed",
        ),
        LimitationFinding(
            "qml.limitation-finding.v1",
            "finding-noise-degradation",
            "high" if noisy_delta < -0.1 or noisy_kernel_error > 0.1 else "medium",
            "model-quality",
            "Declared noise changes the kernel even when QSVM quality is stable",
            (
                f"Mean noisy kernel absolute error: {noisy_kernel_error:.4f}; "
                f"noisy-minus-ideal F1 delta: {noisy_delta:+.4f}."
            ),
            tuple(run.run_id for run in runs if run.profile.execution_mode in {"ideal", "noisy"}),
            ("The channel is a bounded simulator profile, not a hardware characterization.",),
            "observed" if noisy_kernel_error > 0 else "not-observed",
        ),
        LimitationFinding(
            "qml.limitation-finding.v1",
            "finding-mitigation-scope",
            "medium",
            "mitigation",
            "Readout mitigation is partial and can fail to improve the model metric",
            f"Mean mitigated-minus-noisy F1 delta: {mitigation_delta:+.4f}.",
            tuple(
                run.run_id for run in runs if run.profile.execution_mode in {"noisy", "mitigated"}
            ),
            (
                "Only a symmetric readout channel is inverted.",
                "Mitigation is not quantum error correction and does not remove depolarization.",
            ),
            "observed" if mitigation_delta > 0 else "inconclusive",
        ),
        LimitationFinding(
            "qml.limitation-finding.v1",
            "finding-trainability-proxy",
            "medium",
            "trainability",
            "Gradient diagnostics depend on depth, initialization and noise",
            (
                "Deepest tested proxy gradient norm mean: "
                f"{float(deepest['gradient_norm_mean']):.6f}."
            ),
            tuple(str(item["signal_id"]) for item in trainability),
            (
                "This bounded proxy cannot establish a barren plateau.",
                "No production training or hardware execution occurred.",
            ),
            "inconclusive",
        ),
    )


def run_noise_limitations(
    prepared: PreparedDataset,
    protocol: NoiseProtocol | None = None,
) -> NoiseLimitationsReport:
    current = protocol or NoiseProtocol()
    current.validate()
    profiles = noise_profile_registry(current)
    mitigation = mitigation_registry()[0]
    kernel = get_kernel("fidelity-angle-ry-v1")
    train_ids = prepared.snapshot.split.train_ids
    evaluation_ids = prepared.snapshot.split.validation_ids
    train_values, train_labels = _partition(prepared, train_ids)
    evaluation_values, evaluation_labels = _partition(prepared, evaluation_ids)
    all_ids = (*train_ids, *evaluation_ids)
    all_values = np.vstack([train_values, evaluation_values])
    ideal_all = compute_kernel(kernel, all_values)
    train_count = len(train_ids)

    configuration = {
        "snapshot_id": prepared.snapshot.snapshot_id,
        "protocol": current.as_dict(),
        "profiles": [profile.as_dict() for profile in profiles],
        "mitigation": mitigation.as_dict(),
    }
    canonical = json.dumps(configuration, sort_keys=True, separators=(",", ":"))
    comparison_id = f"noise-comparison-{hashlib.sha256(canonical.encode()).hexdigest()[:16]}"
    runs: list[NoiseRun] = []

    for seed in current.seeds:
        seed_runs: list[NoiseRun] = []
        for profile in profiles:
            started = time.perf_counter()
            executed = _execute_kernel(ideal_all, profile, seed, mitigation)
            train_matrix = executed[:train_count, :train_count]
            evaluation_matrix = executed[train_count:, :train_count]
            model = SVC(kernel="precomputed", probability=False, random_state=seed)
            model.fit(train_matrix, train_labels)
            scores = np.asarray(model.decision_function(evaluation_matrix), dtype=float)
            probabilities = 1.0 / (1.0 + np.exp(-np.clip(scores, -30.0, 30.0)))
            predictions = (probabilities >= 0.5).astype(int)
            metrics = _metrics(evaluation_labels, predictions, probabilities)
            metrics["kernel_mae_from_ideal"] = float(np.mean(np.abs(executed - ideal_all)))
            metrics["kernel_max_error_from_ideal"] = float(np.max(np.abs(executed - ideal_all)))
            confusion = confusion_matrix(evaluation_labels, predictions, labels=[0, 1])
            confusion_values = (
                (int(confusion[0, 0]), int(confusion[0, 1])),
                (int(confusion[1, 0]), int(confusion[1, 1])),
            )
            identity = json.dumps(
                {"comparison_id": comparison_id, "profile_id": profile.profile_id, "seed": seed},
                sort_keys=True,
            )
            run_id = f"noise-run-{hashlib.sha256(identity.encode()).hexdigest()[:16]}"
            symmetry_error = float(np.max(np.abs(executed - executed.T)))
            seed_runs.append(
                NoiseRun(
                    schema_version="qml.noise-run.v1",
                    run_id=run_id,
                    comparison_id=comparison_id,
                    profile=profile,
                    seed=seed,
                    snapshot_id=prepared.snapshot.snapshot_id,
                    train_sample_ids=train_ids,
                    evaluation_sample_ids=evaluation_ids,
                    metrics=metrics,
                    confusion_matrix=confusion_values,
                    kernel_checksum=_checksum(profile, all_ids, executed),
                    kernel_symmetry_error=symmetry_error,
                    deltas_from_ideal={},
                    resources={
                        "runtime_seconds": time.perf_counter() - started,
                        "shots": profile.shots,
                        "depth": current.max_depth,
                        "qubits": len(prepared.snapshot.feature_names),
                        "kernel_pair_evaluations": len(all_ids) * (len(all_ids) + 1) // 2,
                        "calibration_shots": (
                            mitigation.calibration_shots
                            if profile.execution_mode == "mitigated"
                            else 0
                        ),
                        "hardware_jobs": 0,
                        "environment": "python-3.12-local-simulator",
                    },
                    calibration=_calibration_manifest(profile, mitigation),
                )
            )
        ideal_metrics = seed_runs[0].metrics
        for run in seed_runs:
            deltas = {
                metric: run.metrics[metric] - ideal_metrics[metric]
                for metric in ("accuracy", "f1", "roc_auc")
            }
            runs.append(replace(run, deltas_from_ideal=deltas))

    uncertainty = _uncertainty(runs)
    trainability = _trainability(current)
    findings = _findings(runs, uncertainty, trainability)
    report_digest = hashlib.sha256(
        json.dumps(
            {"comparison_id": comparison_id, "run_ids": [run.run_id for run in runs]},
            sort_keys=True,
        ).encode()
    ).hexdigest()
    return NoiseLimitationsReport(
        schema_version="qml.noise-limitations-report.v1",
        report_id=f"noise-report-{report_digest[:16]}",
        comparison_id=comparison_id,
        snapshot_id=prepared.snapshot.snapshot_id,
        protocol=current,
        profiles=profiles,
        mitigation=mitigation,
        runs=tuple(runs),
        uncertainty=uncertainty,
        trainability=trainability,
        findings=findings,
        limitations=(
            "All executions are bounded local simulator evidence; no quantum hardware was used.",
            (
                "The noise channel is declared and useful for sensitivity analysis, "
                "not device realism."
            ),
            "Readout inversion is mitigation, not quantum error correction.",
            "Small synthetic data and at most four seeds do not establish general performance.",
            "No result demonstrates quantum advantage or a universal model ranking.",
        ),
        provenance={
            "dataset_sha256": prepared.snapshot.content_hash,
            "preprocessing_fitted_on": prepared.snapshot.preprocessing.fitted_on,
            "paired_factors": ["dataset", "split", "model", "seeds", "budget"],
            "hardware_jobs": 0,
            "quantum_advantage_claimed": False,
            "error_correction_claimed": False,
        },
    )


def workflow_integration_contract() -> dict[str, Any]:
    return {
        "schema_version": "qml.workflow-integration-contract.v1",
        "contract_id": "project-09-v1",
        "read_resources": [
            "/api/v1/datasets/snapshots/{snapshot_id}",
            "/api/v1/benchmarks/reports/{report_id}",
            "/api/v1/noise/reports/{report_id}",
        ],
        "create_resources": [
            "/api/v1/benchmarks/reports",
            "/api/v1/noise/reports",
        ],
        "required_identity": ["schema_version", "snapshot_id", "config hash", "provenance"],
        "execution": "bounded synchronous request only",
        "forbidden_inputs": ["python", "notebook", "qasm", "pickle", "plugin", "remote job"],
        "compatibility": "Consumers validate exact schema versions; no silent adaptation.",
    }
