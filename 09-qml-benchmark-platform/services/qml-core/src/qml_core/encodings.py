from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

from qml_core.models import CircuitGate, EncodingArtifact, EncodingKind, ResourceEstimate

MAX_FEATURES = 8


def _resources(gates: tuple[CircuitGate, ...], qubits: int, dimension: int) -> ResourceEstimate:
    return ResourceEstimate(
        qubits=qubits,
        depth=1 if gates else 0,
        gates=len(gates),
        parameters=sum(gate.parameter is not None for gate in gates),
        state_dimension=dimension,
    )


def _basis(values: np.ndarray) -> EncodingArtifact:
    if len(values) > MAX_FEATURES:
        raise ValueError(f"basis encoding supports at most {MAX_FEATURES} features in this demo")
    rounded = np.rint(values)
    if not np.allclose(values, rounded) or not np.isin(rounded, [0, 1]).all():
        raise ValueError("basis encoding requires binary values containing only 0 or 1")
    bits = rounded.astype(int)
    dimension = 2 ** len(bits)
    index = int("".join(str(bit) for bit in bits), 2) if len(bits) else 0
    state = np.zeros(dimension)
    state[index] = 1.0
    gates = tuple(CircuitGate("X", (wire,)) for wire, bit in enumerate(bits) if bit == 1)
    return EncodingArtifact(
        schema_version="qml.encoding-artifact.v1",
        encoding="basis",
        input_values=tuple(float(value) for value in values),
        encoded_values=tuple(float(value) for value in bits),
        padding=0,
        normalization_norm=float(np.linalg.norm(bits)),
        statevector_real=tuple(float(value) for value in state),
        gates=gates,
        resources=_resources(gates, len(bits), dimension),
        warnings=("Binary thresholding is not applied; input must already be binary.",),
        backend="numpy-reference",
    )


def _angle(values: np.ndarray) -> EncodingArtifact:
    if len(values) > MAX_FEATURES:
        raise ValueError(f"angle encoding supports at most {MAX_FEATURES} features in this demo")
    clipped = np.clip(values, -1.0, 1.0)
    angles = (clipped + 1.0) * math.pi / 2.0
    state = np.array([1.0])
    for angle in angles:
        state = np.kron(state, np.array([math.cos(angle / 2), math.sin(angle / 2)]))
    gates = tuple(CircuitGate("RY", (wire,), float(angle)) for wire, angle in enumerate(angles))
    warnings: tuple[str, ...] = ()
    if not np.allclose(values, clipped):
        warnings = ("Values outside [-1, 1] were clipped before angle mapping.",)
    return EncodingArtifact(
        schema_version="qml.encoding-artifact.v1",
        encoding="angle",
        input_values=tuple(float(value) for value in values),
        encoded_values=tuple(float(value) for value in angles),
        padding=0,
        normalization_norm=float(np.linalg.norm(values)),
        statevector_real=tuple(float(value) for value in state),
        gates=gates,
        resources=_resources(gates, len(values), len(state)),
        warnings=warnings,
        backend="numpy-reference",
    )


def _amplitude(values: np.ndarray) -> EncodingArtifact:
    if len(values) > MAX_FEATURES:
        raise ValueError(
            f"amplitude encoding supports at most {MAX_FEATURES} features in this demo"
        )
    norm = float(np.linalg.norm(values))
    if math.isclose(norm, 0.0):
        raise ValueError("amplitude encoding cannot normalize an all-zero vector")
    qubits = max(1, math.ceil(math.log2(len(values))))
    dimension = 2**qubits
    padding = dimension - len(values)
    padded = np.pad(values, (0, padding))
    state = padded / norm
    gates = (CircuitGate("STATE_PREPARATION", tuple(range(qubits))),)
    return EncodingArtifact(
        schema_version="qml.encoding-artifact.v1",
        encoding="amplitude",
        input_values=tuple(float(value) for value in values),
        encoded_values=tuple(float(value) for value in state),
        padding=padding,
        normalization_norm=norm,
        statevector_real=tuple(float(value) for value in state),
        gates=gates,
        resources=_resources(gates, qubits, dimension),
        warnings=("State preparation cost is represented as one conceptual operation.",),
        backend="numpy-reference",
    )


def encode(values: Sequence[float], kind: EncodingKind) -> EncodingArtifact:
    array = np.asarray(tuple(values), dtype=float)
    if array.ndim != 1 or len(array) == 0:
        raise ValueError("encoding input must be a non-empty one-dimensional vector")
    if not np.isfinite(array).all():
        raise ValueError("encoding input must contain only finite numeric values")
    if kind == "basis":
        return _basis(array)
    if kind == "angle":
        return _angle(array)
    if kind == "amplitude":
        return _amplitude(array)
    raise ValueError(f"unsupported encoding: {kind}")
