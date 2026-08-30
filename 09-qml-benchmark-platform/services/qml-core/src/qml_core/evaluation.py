from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Sequence
from typing import Any

import numpy as np
import pennylane as qml
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.svm import SVC

from qml_core.benchmark_models import EvaluationProtocol, ModelRun, ModelSpec
from qml_core.kernels import compute_kernel, get_kernel


def model_registry(protocol: EvaluationProtocol) -> tuple[ModelSpec, ...]:
    return (
        ModelSpec("qml.model-spec.v1", "logistic-v1", "logistic", None, 100),
        ModelSpec("qml.model-spec.v1", "rbf-svm-v1", "rbf-svm", "rbf-gamma05-v1", 100),
        ModelSpec(
            "qml.model-spec.v1",
            "qsvm-fidelity-v1",
            "qsvm",
            "fidelity-angle-ry-v1",
            100,
        ),
        ModelSpec(
            "qml.model-spec.v1",
            "vqc-angle-ry-v1",
            "vqc",
            None,
            protocol.max_vqc_iterations,
        ),
    )


def _probability(score: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(score, -30.0, 30.0)))


def _metrics(
    labels: np.ndarray,
    predictions: np.ndarray,
    probability: np.ndarray,
) -> dict[str, float]:
    return {
        "accuracy": float(accuracy_score(labels, predictions)),
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "f1": float(f1_score(labels, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(labels, probability)),
    }


def _vqc_scores(
    train_values: np.ndarray,
    train_labels: np.ndarray,
    evaluation_values: np.ndarray,
    seed: int,
    iterations: int,
) -> tuple[np.ndarray, list[dict[str, float]], int]:
    qubits = train_values.shape[1]
    device = qml.device("default.qubit", wires=qubits)

    @qml.qnode(device)
    def circuit(features: np.ndarray, weights: np.ndarray) -> Any:
        qml.AngleEmbedding(np.clip(features, -1.0, 1.0), wires=range(qubits), rotation="Y")
        for wire in range(qubits):
            qml.RY(weights[wire], wires=wire)
        for wire in range(qubits - 1):
            qml.CNOT(wires=[wire, wire + 1])
        return qml.expval(qml.PauliZ(0))

    generator = np.random.default_rng(seed)
    weights: np.ndarray = np.asarray(
        generator.normal(0.0, 0.15, size=qubits),
        dtype=np.float64,
    )
    history: list[dict[str, float]] = []
    epsilon = 0.08
    learning_rate = 0.2
    evaluations = 0

    def probabilities(current: np.ndarray, values: np.ndarray) -> np.ndarray:
        nonlocal evaluations
        result = np.asarray([(1.0 - float(circuit(row, current))) / 2.0 for row in values])
        evaluations += len(values)
        return np.clip(result, 1e-6, 1.0 - 1e-6)

    def loss(current: np.ndarray) -> float:
        predicted = probabilities(current, train_values)
        return float(
            -np.mean(
                train_labels * np.log(predicted) + (1.0 - train_labels) * np.log(1.0 - predicted)
            )
        )

    for iteration in range(iterations):
        baseline = loss(weights)
        gradient = np.zeros_like(weights)
        for index in range(qubits):
            forward = weights.copy()
            backward = weights.copy()
            forward[index] += epsilon
            backward[index] -= epsilon
            gradient[index] = (loss(forward) - loss(backward)) / (2.0 * epsilon)
        weights -= learning_rate * gradient
        history.append(
            {
                "iteration": float(iteration + 1),
                "loss": baseline,
                "gradient_norm": float(np.linalg.norm(gradient)),
            }
        )
    return probabilities(weights, evaluation_values), history, evaluations


def evaluate_model(
    spec: ModelSpec,
    protocol: EvaluationProtocol,
    plan_id: str,
    seed: int,
    train_values: np.ndarray,
    train_labels: np.ndarray,
    evaluation_values: np.ndarray,
    evaluation_labels: np.ndarray,
    train_sample_ids: Sequence[str],
    evaluation_sample_ids: Sequence[str],
) -> ModelRun:
    protocol.validate()
    spec.validate(protocol)
    started = time.perf_counter()
    diagnostics: dict[str, Any] = {"converged": True}
    circuit_evaluations = 0
    pair_evaluations = 0

    if spec.kind == "logistic":
        logistic_model = LogisticRegression(random_state=seed, max_iter=spec.max_iterations)
        logistic_model.fit(train_values, train_labels)
        probability = logistic_model.predict_proba(evaluation_values)[:, 1]
    elif spec.kind == "rbf-svm":
        rbf_model = SVC(kernel="rbf", gamma=0.5, probability=True, random_state=seed)
        rbf_model.fit(train_values, train_labels)
        probability = rbf_model.predict_proba(evaluation_values)[:, 1]
    elif spec.kind == "qsvm":
        kernel = get_kernel("fidelity-angle-ry-v1")
        train_matrix = compute_kernel(kernel, train_values)
        evaluation_matrix = compute_kernel(kernel, evaluation_values, train_values)
        qsvm_model = SVC(kernel="precomputed", probability=False, random_state=seed)
        qsvm_model.fit(train_matrix, train_labels)
        probability = _probability(qsvm_model.decision_function(evaluation_matrix))
        circuit_evaluations = len(train_values) + len(evaluation_values)
        pair_evaluations = len(train_values) ** 2 + len(evaluation_values) * len(train_values)
        diagnostics["support_vectors"] = int(len(qsvm_model.support_))
        diagnostics["probability_transform"] = "uncalibrated sigmoid of decision function"
    else:
        probability, history, circuit_evaluations = _vqc_scores(
            train_values,
            train_labels,
            evaluation_values,
            seed,
            spec.max_iterations,
        )
        diagnostics["objective_history"] = history

    predictions = (probability >= 0.5).astype(int)
    metrics = _metrics(evaluation_labels, predictions, probability)
    confusion = confusion_matrix(evaluation_labels, predictions, labels=[0, 1])
    confusion_values = (
        (int(confusion[0, 0]), int(confusion[0, 1])),
        (int(confusion[1, 0]), int(confusion[1, 1])),
    )
    runtime = time.perf_counter() - started
    identity = json.dumps(
        {"plan_id": plan_id, "model_id": spec.model_id, "seed": seed},
        sort_keys=True,
    )
    run_id = f"run-{hashlib.sha256(identity.encode()).hexdigest()[:16]}"
    resources: dict[str, int | float | str] = {
        "runtime_seconds": runtime,
        "qubits": train_values.shape[1] if spec.kind in {"qsvm", "vqc"} else 0,
        "depth": 1 if spec.kind == "qsvm" else (2 if spec.kind == "vqc" else 0),
        "shots": 0,
        "parameters": train_values.shape[1] if spec.kind == "vqc" else 0,
        "circuit_evaluations": circuit_evaluations,
        "similarity_pair_evaluations": pair_evaluations,
        "environment": "python-3.12-local-statevector",
        "measurement": "time.perf_counter wall clock",
    }
    return ModelRun(
        schema_version="qml.model-run.v1",
        run_id=run_id,
        plan_id=plan_id,
        model=spec,
        seed=seed,
        split=protocol.split,
        train_sample_ids=tuple(train_sample_ids),
        evaluation_sample_ids=tuple(evaluation_sample_ids),
        metrics=metrics,
        confusion_matrix=confusion_values,
        resources=resources,
        diagnostics=diagnostics,
    )


def aggregate_runs(runs: Sequence[ModelRun]) -> tuple[dict[str, Any], ...]:
    aggregates: list[dict[str, Any]] = []
    model_ids = sorted({run.model.model_id for run in runs})
    for model_id in model_ids:
        group = [run for run in runs if run.model.model_id == model_id]
        metric_summary: dict[str, dict[str, float]] = {}
        for metric in ("accuracy", "precision", "recall", "f1", "roc_auc"):
            values = np.asarray([float(run.metrics[metric]) for run in group])
            metric_summary[metric] = {
                "mean": float(np.mean(values)),
                "std": float(np.std(values)),
                "minimum": float(np.min(values)),
                "maximum": float(np.max(values)),
            }
        aggregates.append(
            {
                "model_id": model_id,
                "repetitions": len(group),
                "metrics": metric_summary,
                "claim": "Local bounded comparison only; not evidence of quantum advantage.",
            }
        )
    return tuple(aggregates)
