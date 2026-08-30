from __future__ import annotations

import numpy as np

from qml_core.datasets import PreparedDataset, prepare_dataset
from tests.python.conftest import ROOT


def prepared() -> PreparedDataset:
    return prepare_dataset(
        ROOT / "data/datasets/qml_encoding_demo_v1.csv",
        ROOT / "data/datasets/qml_encoding_demo_v1.manifest.json",
    )


def test_split_is_disjoint_complete_and_deterministic() -> None:
    first = prepared()
    second = prepared()
    split = first.snapshot.split
    train = set(split.train_ids)
    validation = set(split.validation_ids)
    test = set(split.test_ids)
    assert not train & validation
    assert not train & test
    assert not validation & test
    assert len(train | validation | test) == first.snapshot.row_count
    assert split == second.snapshot.split
    assert first.snapshot.content_hash == second.snapshot.content_hash


def test_scaler_is_fitted_only_on_train_rows() -> None:
    result = prepared()
    train = result.raw["sample_id"].isin(result.snapshot.split.train_ids)
    values = result.raw.loc[train, list(result.snapshot.feature_names)].to_numpy()
    assert np.allclose(result.snapshot.preprocessing.means, values.mean(axis=0))
    assert result.snapshot.preprocessing.fitted_on == "train"
    transformed_train = result.transformed.loc[train, list(result.snapshot.feature_names)]
    assert np.allclose(transformed_train.mean(axis=0), 0.0, atol=1e-12)
