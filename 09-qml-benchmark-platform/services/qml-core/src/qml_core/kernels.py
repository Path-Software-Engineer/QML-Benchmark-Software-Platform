from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence

import numpy as np

from qml_core.benchmark_models import KernelMatrixArtifact, KernelSpec
from qml_core.encodings import encode


def kernel_registry() -> tuple[KernelSpec, ...]:
    return (
        KernelSpec("qml.kernel-spec.v1", "linear-v1", "linear"),
        KernelSpec(
            "qml.kernel-spec.v1",
            "polynomial-d2-v1",
            "polynomial",
            gamma=0.5,
            degree=2,
        ),
        KernelSpec("qml.kernel-spec.v1", "rbf-gamma05-v1", "rbf", gamma=0.5),
        KernelSpec(
            "qml.kernel-spec.v1",
            "fidelity-angle-ry-v1",
            "quantum-fidelity",
            feature_map="angle-ry-v1",
            backend="statevector-reference",
        ),
    )


def get_kernel(kernel_id: str) -> KernelSpec:
    for spec in kernel_registry():
        if spec.kernel_id == kernel_id:
            return spec
    raise KeyError(f"unknown kernel_id: {kernel_id}")


def _quantum_states(values: np.ndarray) -> np.ndarray:
    return np.asarray([encode(row, "angle").statevector_real for row in values], dtype=float)


def compute_kernel(
    spec: KernelSpec,
    left: np.ndarray,
    right: np.ndarray | None = None,
) -> np.ndarray:
    spec.validate()
    right_values = left if right is None else right
    if left.ndim != 2 or right_values.ndim != 2 or left.shape[1] != right_values.shape[1]:
        raise ValueError("kernel inputs must be compatible two-dimensional matrices")
    if not np.isfinite(left).all() or not np.isfinite(right_values).all():
        raise ValueError("kernel inputs must contain finite values")
    if spec.kind == "linear":
        return left @ right_values.T
    if spec.kind == "polynomial":
        return (spec.gamma * (left @ right_values.T) + spec.coefficient) ** spec.degree
    if spec.kind == "rbf":
        distances = np.sum((left[:, None, :] - right_values[None, :, :]) ** 2, axis=2)
        return np.exp(-spec.gamma * distances)
    left_states = _quantum_states(left)
    right_states = left_states if right is None else _quantum_states(right_values)
    return np.abs(left_states @ right_states.T) ** 2


def matrix_artifact(
    spec: KernelSpec,
    values: np.ndarray,
    sample_ids: Sequence[str],
) -> KernelMatrixArtifact:
    if len(values) != len(sample_ids):
        raise ValueError("sample order length must match the kernel matrix input")
    matrix = compute_kernel(spec, values)
    symmetry_error = float(np.max(np.abs(matrix - matrix.T)))
    symmetric = bool(np.allclose(matrix, matrix.T, atol=1e-10))
    if not symmetric:
        raise ValueError("square kernel matrix failed the symmetry invariant")
    rounded = np.round(matrix, 12)
    identity = json.dumps(
        {
            "kernel": spec.as_dict(),
            "sample_ids": list(sample_ids),
            "values": rounded.tolist(),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    checksum = hashlib.sha256(identity.encode()).hexdigest()
    count = len(matrix)
    centering = np.eye(count) - np.ones((count, count)) / count
    centered = centering @ matrix @ centering
    eigenvalues, eigenvectors = np.linalg.eigh(centered)
    order = np.argsort(eigenvalues)[::-1][:2]
    coordinates = eigenvectors[:, order] * np.sqrt(np.clip(eigenvalues[order], 0.0, None))
    for column in range(coordinates.shape[1]):
        anchor = int(np.argmax(np.abs(coordinates[:, column])))
        if coordinates[anchor, column] < 0:
            coordinates[:, column] *= -1
    if coordinates.shape[1] == 1:
        coordinates = np.column_stack([coordinates, np.zeros(count)])
    projection_rows: list[dict[str, float | str]] = []
    for index, sample_id in enumerate(sample_ids):
        projection_rows.append(
            {
                "sample_id": str(sample_id),
                "component_1": float(coordinates[index, 0]),
                "component_2": float(coordinates[index, 1]),
            }
        )
    projection = tuple(projection_rows)
    features = values.shape[1]
    pair_count = len(values) * (len(values) + 1) // 2
    resources: dict[str, int | float | str] = {
        "backend": spec.backend,
        "pair_evaluations": pair_count,
        "qubits": features if spec.kind == "quantum-fidelity" else 0,
        "depth": 1 if spec.kind == "quantum-fidelity" else 0,
        "shots": 0,
    }
    return KernelMatrixArtifact(
        schema_version="qml.kernel-matrix.v1",
        matrix_id=f"matrix-{checksum[:16]}",
        kernel=spec,
        sample_ids=tuple(sample_ids),
        shape=(int(matrix.shape[0]), int(matrix.shape[1])),
        dtype=str(matrix.dtype),
        values=tuple(tuple(float(value) for value in row) for row in rounded),
        symmetric=symmetric,
        symmetry_error=symmetry_error,
        checksum=checksum,
        resources=resources,
        projection_method="centered-kernel-pca",
        projection_seed=0,
        projection=projection,
    )
