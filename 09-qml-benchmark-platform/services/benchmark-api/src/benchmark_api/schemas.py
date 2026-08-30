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
