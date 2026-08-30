from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

type EncodingKind = Literal["basis", "angle", "amplitude"]


@dataclass(frozen=True)
class CircuitGate:
    name: str
    wires: tuple[int, ...]
    parameter: float | None = None


@dataclass(frozen=True)
class ResourceEstimate:
    qubits: int
    depth: int
    gates: int
    parameters: int
    state_dimension: int


@dataclass(frozen=True)
class EncodingArtifact:
    schema_version: str
    encoding: EncodingKind
    input_values: tuple[float, ...]
    encoded_values: tuple[float, ...]
    padding: int
    normalization_norm: float
    statevector_real: tuple[float, ...]
    gates: tuple[CircuitGate, ...]
    resources: ResourceEstimate
    warnings: tuple[str, ...]
    backend: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SplitDefinition:
    seed: int
    train_ids: tuple[str, ...]
    validation_ids: tuple[str, ...]
    test_ids: tuple[str, ...]


@dataclass(frozen=True)
class PreprocessingSpec:
    method: Literal["standard-scaler"]
    fitted_on: Literal["train"]
    means: tuple[float, ...]
    scales: tuple[float, ...]


@dataclass(frozen=True)
class DatasetSnapshot:
    schema_version: str
    snapshot_id: str
    dataset_id: str
    dataset_version: str
    content_hash: str
    feature_names: tuple[str, ...]
    target_name: str
    row_count: int
    source: str
    license: str
    split: SplitDefinition
    preprocessing: PreprocessingSpec
    preview_rows: tuple[dict[str, Any], ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
