from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class PreviewRequest(BaseModel):
    snapshot_id: str
    sample_id: str
    encoding: Literal["basis", "angle", "amplitude"]
    values: list[float] | None = Field(default=None, max_length=8)

    @field_validator("values")
    @classmethod
    def reject_empty_override(cls, value: list[float] | None) -> list[float] | None:
        if value is not None and not value:
            raise ValueError("values override cannot be empty")
        return value


class ValidationRequest(BaseModel):
    encoding: Literal["basis", "angle", "amplitude"]
    values: list[float] = Field(min_length=1, max_length=8)


class PreviewResponse(BaseModel):
    schema_version: str
    preview_id: str
    snapshot_id: str
    sample_id: str
    artifact: dict[str, Any]
    adapters: dict[str, Any]
    provenance: dict[str, Any]


class BenchmarkRequest(BaseModel):
    snapshot_id: str
    seeds: list[int] = Field(default=[2409, 2410], min_length=1, max_length=3)
    vqc_iterations: int = Field(default=4, ge=1, le=8)

    @field_validator("seeds")
    @classmethod
    def require_unique_seeds(cls, value: list[int]) -> list[int]:
        if len(set(value)) != len(value):
            raise ValueError("benchmark seeds must be unique")
        return value


class EvidenceImportRequest(BaseModel):
    bundle: dict[str, Any]


class NoiseReportRequest(BaseModel):
    snapshot_id: str
    seeds: list[int] = Field(default=[3501, 3502, 3503], min_length=1, max_length=4)
    shots: int = Field(default=256, ge=64, le=2048)
    noise_strength: float = Field(default=0.08, ge=0.0, le=0.25)
    readout_error: float = Field(default=0.04, ge=0.0, lt=0.2)
    max_depth: int = Field(default=4, ge=1, le=8)

    @field_validator("seeds")
    @classmethod
    def require_unique_noise_seeds(cls, value: list[int]) -> list[int]:
        if len(set(value)) != len(value):
            raise ValueError("noise benchmark seeds must be unique")
        return value
