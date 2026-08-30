from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

type KernelKind = Literal["linear", "polynomial", "rbf", "quantum-fidelity"]
type ModelKind = Literal["logistic", "rbf-svm", "qsvm", "vqc"]


@dataclass(frozen=True)
class EvaluationProtocol:
    schema_version: str = "qml.evaluation-protocol.v1"
    protocol_id: str = "sprint-02-local-v1"
    split: Literal["validation"] = "validation"
    seeds: tuple[int, ...] = (2409, 2410)
    repetitions: int = 2
    max_samples: int = 20
    max_features: int = 3
    max_vqc_iterations: int = 4
    metrics: tuple[str, ...] = ("accuracy", "precision", "recall", "f1", "roc_auc")

    def validate(self) -> None:
        if self.repetitions != len(self.seeds) or not 1 <= self.repetitions <= 3:
            raise ValueError("protocol repetitions must match one to three declared seeds")
        if self.max_samples > 32 or self.max_features > 8:
            raise ValueError("protocol exceeds the bounded local simulation budget")
        if not 1 <= self.max_vqc_iterations <= 8:
            raise ValueError("VQC iterations must remain between 1 and 8")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class KernelSpec:
    schema_version: str
    kernel_id: str
    kind: KernelKind
    gamma: float = 1.0
    degree: int = 2
    coefficient: float = 1.0
    feature_map: str | None = None
    backend: str = "numpy"

    def validate(self) -> None:
        if self.gamma <= 0:
            raise ValueError("kernel gamma must be positive")
        if self.kind == "polynomial" and not 2 <= self.degree <= 3:
            raise ValueError("polynomial degree must be 2 or 3")
        if self.kind == "quantum-fidelity" and self.feature_map != "angle-ry-v1":
            raise ValueError("quantum kernel requires the allowlisted angle-ry-v1 feature map")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ModelSpec:
    schema_version: str
    model_id: str
    kind: ModelKind
    kernel_id: str | None
    max_iterations: int
    hyperparameter_trials: int = 1

    def validate(self, protocol: EvaluationProtocol) -> None:
        if self.hyperparameter_trials != 1:
            raise ValueError("Sprint 2 permits one declared configuration per model")
        if self.kind == "vqc" and self.max_iterations > protocol.max_vqc_iterations:
            raise ValueError("VQC configuration exceeds the evaluation protocol budget")
        if self.max_iterations < 1 or self.max_iterations > 200:
            raise ValueError("model iteration budget is outside the allowlisted range")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class KernelMatrixArtifact:
    schema_version: str
    matrix_id: str
    kernel: KernelSpec
    sample_ids: tuple[str, ...]
    shape: tuple[int, int]
    dtype: str
    values: tuple[tuple[float, ...], ...]
    symmetric: bool
    symmetry_error: float
    checksum: str
    resources: dict[str, int | float | str]
    projection_method: str
    projection_seed: int
    projection: tuple[dict[str, float | str], ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ModelRun:
    schema_version: str
    run_id: str
    plan_id: str
    model: ModelSpec
    seed: int
    split: str
    train_sample_ids: tuple[str, ...]
    evaluation_sample_ids: tuple[str, ...]
    metrics: dict[str, float]
    confusion_matrix: tuple[tuple[int, int], tuple[int, int]]
    resources: dict[str, int | float | str]
    diagnostics: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BenchmarkReport:
    schema_version: str
    report_id: str
    plan_id: str
    snapshot_id: str
    protocol: EvaluationProtocol
    config_hash: str
    kernel_matrices: tuple[KernelMatrixArtifact, ...]
    runs: tuple[ModelRun, ...]
    aggregates: tuple[dict[str, Any], ...]
    limitations: tuple[str, ...]
    provenance: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
