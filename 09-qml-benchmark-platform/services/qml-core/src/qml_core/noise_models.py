from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

type ExecutionMode = Literal["ideal", "shot-based", "noisy", "mitigated"]
type FindingSeverity = Literal["low", "medium", "high"]
type FindingStatus = Literal["observed", "not-observed", "inconclusive"]


@dataclass(frozen=True)
class NoiseProtocol:
    schema_version: str = "qml.noise-protocol.v1"
    protocol_id: str = "sprint-03-local-v1"
    seeds: tuple[int, ...] = (3501, 3502, 3503)
    shots: int = 256
    noise_strength: float = 0.08
    readout_error: float = 0.04
    max_depth: int = 4
    model_id: str = "qsvm-fidelity-v1"
    split: Literal["validation"] = "validation"

    def validate(self) -> None:
        if not 1 <= len(self.seeds) <= 4 or len(set(self.seeds)) != len(self.seeds):
            raise ValueError("noise protocol requires one to four unique seeds")
        if not 64 <= self.shots <= 2048:
            raise ValueError("shots must remain between 64 and 2048")
        if not 0.0 <= self.noise_strength <= 0.25:
            raise ValueError("noise strength must remain between 0 and 0.25")
        if not 0.0 <= self.readout_error < 0.2:
            raise ValueError("readout error must remain between 0 and 0.2")
        if not 1 <= self.max_depth <= 8:
            raise ValueError("trainability depth must remain between 1 and 8")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NoiseProfile:
    schema_version: str
    profile_id: str
    execution_mode: ExecutionMode
    backend: str
    shots: int
    depolarizing_strength: float
    readout_error: float
    mitigation_id: str | None

    def validate(self) -> None:
        if self.execution_mode == "ideal" and (
            self.shots != 0 or self.depolarizing_strength != 0 or self.readout_error != 0
        ):
            raise ValueError("ideal profile cannot declare shots or noise")
        if self.execution_mode != "ideal" and not 64 <= self.shots <= 2048:
            raise ValueError("sampled profiles require 64 to 2048 shots")
        if self.execution_mode == "mitigated" and self.mitigation_id is None:
            raise ValueError("mitigated profile requires an allowlisted mitigation")
        if self.execution_mode != "mitigated" and self.mitigation_id is not None:
            raise ValueError("only mitigated profiles may reference mitigation")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MitigationSpec:
    schema_version: str
    mitigation_id: str
    method: Literal["symmetric-readout-inversion"]
    calibration_shots: int
    regularization: float
    applicability: str

    def validate(self) -> None:
        if not 64 <= self.calibration_shots <= 4096:
            raise ValueError("calibration shots must remain between 64 and 4096")
        if not 0.0 <= self.regularization <= 0.1:
            raise ValueError("mitigation regularization is outside the allowlist")

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NoiseRun:
    schema_version: str
    run_id: str
    comparison_id: str
    profile: NoiseProfile
    seed: int
    snapshot_id: str
    train_sample_ids: tuple[str, ...]
    evaluation_sample_ids: tuple[str, ...]
    metrics: dict[str, float]
    confusion_matrix: tuple[tuple[int, int], tuple[int, int]]
    kernel_checksum: str
    kernel_symmetry_error: float
    deltas_from_ideal: dict[str, float]
    resources: dict[str, int | float | str]
    calibration: dict[str, Any] | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LimitationFinding:
    schema_version: str
    finding_id: str
    severity: FindingSeverity
    scope: str
    title: str
    observation: str
    evidence_links: tuple[str, ...]
    caveats: tuple[str, ...]
    status: FindingStatus

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NoiseLimitationsReport:
    schema_version: str
    report_id: str
    comparison_id: str
    snapshot_id: str
    protocol: NoiseProtocol
    profiles: tuple[NoiseProfile, ...]
    mitigation: MitigationSpec
    runs: tuple[NoiseRun, ...]
    uncertainty: tuple[dict[str, Any], ...]
    trainability: tuple[dict[str, Any], ...]
    findings: tuple[LimitationFinding, ...]
    limitations: tuple[str, ...]
    provenance: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
