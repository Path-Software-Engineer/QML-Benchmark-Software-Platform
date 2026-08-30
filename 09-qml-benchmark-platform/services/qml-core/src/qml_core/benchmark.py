from __future__ import annotations

import hashlib
import json
from typing import Any

import numpy as np

from qml_core.benchmark_models import BenchmarkReport, EvaluationProtocol
from qml_core.datasets import PreparedDataset
from qml_core.evaluation import aggregate_runs, evaluate_model, model_registry
from qml_core.kernels import kernel_registry, matrix_artifact


def _partition(
    prepared: PreparedDataset,
    identifiers: tuple[str, ...],
) -> tuple[np.ndarray, np.ndarray]:
    frame = prepared.transformed.set_index("sample_id").loc[list(identifiers)]
    values = frame[list(prepared.snapshot.feature_names)].to_numpy(dtype=float)
    classes = sorted(prepared.raw[prepared.snapshot.target_name].astype(str).unique())
    if len(classes) != 2:
        raise ValueError("Sprint 2 benchmark requires exactly two target classes")
    mapping = {label: index for index, label in enumerate(classes)}
    labels = frame[prepared.snapshot.target_name].astype(str).map(mapping).to_numpy(dtype=int)
    return values, labels


def run_benchmark(
    prepared: PreparedDataset,
    protocol: EvaluationProtocol | None = None,
) -> BenchmarkReport:
    current = protocol or EvaluationProtocol()
    current.validate()
    if prepared.snapshot.row_count > current.max_samples:
        raise ValueError("dataset exceeds the declared evaluation protocol sample budget")
    if len(prepared.snapshot.feature_names) > current.max_features:
        raise ValueError("dataset exceeds the declared evaluation protocol feature budget")

    train_ids = prepared.snapshot.split.train_ids
    validation_ids = prepared.snapshot.split.validation_ids
    train_values, train_labels = _partition(prepared, train_ids)
    validation_values, validation_labels = _partition(prepared, validation_ids)
    all_ids = (*train_ids, *validation_ids)
    all_values = np.vstack([train_values, validation_values])
    matrices = tuple(matrix_artifact(spec, all_values, all_ids) for spec in kernel_registry())

    configuration: dict[str, Any] = {
        "snapshot_id": prepared.snapshot.snapshot_id,
        "protocol": current.as_dict(),
        "kernels": [spec.as_dict() for spec in kernel_registry()],
        "models": [spec.as_dict() for spec in model_registry(current)],
    }
    canonical = json.dumps(configuration, sort_keys=True, separators=(",", ":"))
    config_hash = hashlib.sha256(canonical.encode()).hexdigest()
    plan_id = f"plan-{config_hash[:16]}"
    runs = tuple(
        evaluate_model(
            model,
            current,
            plan_id,
            seed,
            train_values,
            train_labels,
            validation_values,
            validation_labels,
            train_ids,
            validation_ids,
        )
        for seed in current.seeds
        for model in model_registry(current)
    )
    report_identity = hashlib.sha256(
        json.dumps(
            {"plan_id": plan_id, "run_ids": [run.run_id for run in runs]},
            sort_keys=True,
        ).encode()
    ).hexdigest()
    return BenchmarkReport(
        schema_version="qml.benchmark-report.v1",
        report_id=f"report-{report_identity[:16]}",
        plan_id=plan_id,
        snapshot_id=prepared.snapshot.snapshot_id,
        protocol=current,
        config_hash=config_hash,
        kernel_matrices=matrices,
        runs=runs,
        aggregates=aggregate_runs(runs),
        limitations=(
            "Synthetic dataset with twenty samples; external validity is intentionally limited.",
            "Statevector simulation excludes hardware noise and queue behavior.",
            "Two seeds describe local variability; they do not establish a universal ranking.",
            "No result in this report demonstrates quantum advantage.",
        ),
        provenance={
            "dataset_sha256": prepared.snapshot.content_hash,
            "preprocessing_fitted_on": prepared.snapshot.preprocessing.fitted_on,
            "sample_order_bound": True,
            "hardware_jobs": 0,
            "quantum_advantage_claimed": False,
        },
    )
