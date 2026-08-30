from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from qml_core.models import DatasetSnapshot, PreprocessingSpec, SplitDefinition


@dataclass(frozen=True)
class PreparedDataset:
    snapshot: DatasetSnapshot
    raw: pd.DataFrame
    transformed: pd.DataFrame


def canonical_sha256(path: Path) -> str:
    frame = pd.read_csv(path)
    canonical = frame.to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _split_ids(frame: pd.DataFrame, target: str, seed: int) -> SplitDefinition:
    identifiers = frame["sample_id"].astype(str).to_numpy()
    labels = frame[target].to_numpy()
    train_ids, remainder_ids, _, remainder_labels = train_test_split(
        identifiers,
        labels,
        test_size=0.4,
        random_state=seed,
        stratify=labels,
    )
    validation_ids, test_ids = train_test_split(
        remainder_ids,
        test_size=0.5,
        random_state=seed,
        stratify=remainder_labels,
    )
    return SplitDefinition(
        seed=seed,
        train_ids=tuple(sorted(train_ids.tolist())),
        validation_ids=tuple(sorted(validation_ids.tolist())),
        test_ids=tuple(sorted(test_ids.tolist())),
    )


def _assert_disjoint(split: SplitDefinition, row_count: int) -> None:
    groups = [set(split.train_ids), set(split.validation_ids), set(split.test_ids)]
    if any(left & right for index, left in enumerate(groups) for right in groups[index + 1 :]):
        raise ValueError("train, validation and test splits must be disjoint")
    if len(set().union(*groups)) != row_count:
        raise ValueError("split membership must cover every sample exactly once")


def prepare_dataset(
    csv_path: Path,
    manifest_path: Path,
    *,
    seed: int = 2409,
) -> PreparedDataset:
    manifest: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    frame = pd.read_csv(csv_path)
    feature_names = tuple(str(value) for value in manifest["feature_names"])
    target_name = str(manifest["target_name"])
    required = {"sample_id", target_name, *feature_names}
    if not required.issubset(frame.columns):
        raise ValueError(f"dataset is missing columns: {sorted(required - set(frame.columns))}")
    if frame["sample_id"].duplicated().any():
        raise ValueError("sample_id values must be unique")
    if frame[list(feature_names)].isna().any().any():
        raise ValueError("encoding features cannot contain missing values")

    split = _split_ids(frame, target_name, seed)
    _assert_disjoint(split, len(frame))
    train_mask = frame["sample_id"].astype(str).isin(split.train_ids)
    scaler = StandardScaler().fit(frame.loc[train_mask, list(feature_names)])
    transformed = frame.copy()
    transformed[list(feature_names)] = scaler.transform(frame[list(feature_names)])

    digest = canonical_sha256(csv_path)
    if digest != manifest.get("content_sha256"):
        raise ValueError("dataset content does not match its versioned SHA-256 manifest")
    snapshot_id = f"{manifest['dataset_id']}-{manifest['version']}-{digest[:12]}"
    preview = tuple(
        {
            "sample_id": str(row["sample_id"]),
            **{name: float(row[name]) for name in feature_names},
            target_name: str(row[target_name]),
        }
        for row in frame.head(6).to_dict(orient="records")
    )
    snapshot = DatasetSnapshot(
        schema_version="qml.dataset-snapshot.v1",
        snapshot_id=snapshot_id,
        dataset_id=str(manifest["dataset_id"]),
        dataset_version=str(manifest["version"]),
        content_hash=digest,
        feature_names=feature_names,
        target_name=target_name,
        row_count=len(frame),
        source=str(manifest["source"]),
        license=str(manifest["license"]),
        split=split,
        preprocessing=PreprocessingSpec(
            method="standard-scaler",
            fitted_on="train",
            means=tuple(float(value) for value in scaler.mean_),
            scales=tuple(float(value) for value in scaler.scale_),
        ),
        preview_rows=preview,
    )
    return PreparedDataset(snapshot=snapshot, raw=frame, transformed=transformed)


def select_sample(prepared: PreparedDataset, sample_id: str) -> tuple[float, ...]:
    rows = prepared.transformed.loc[prepared.transformed["sample_id"] == sample_id]
    if rows.empty:
        raise KeyError(f"unknown sample_id: {sample_id}")
    row = rows.iloc[0]
    return tuple(float(row[name]) for name in prepared.snapshot.feature_names)
