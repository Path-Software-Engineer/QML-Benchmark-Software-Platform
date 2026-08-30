from __future__ import annotations

import math

import numpy as np
import pytest

from qml_core.adapters import cross_check
from qml_core.encodings import encode


def test_basis_encoding_prepares_expected_state() -> None:
    artifact = encode([1, 0, 1], "basis")
    assert artifact.resources.qubits == 3
    assert artifact.statevector_real[5] == 1.0
    assert [gate.name for gate in artifact.gates] == ["X", "X"]


def test_basis_rejects_non_binary_input() -> None:
    with pytest.raises(ValueError, match="binary"):
        encode([0.0, 0.5], "basis")


def test_angle_maps_interval_and_normalizes_state() -> None:
    artifact = encode([-1.0, 0.0, 1.0], "angle")
    assert np.allclose(artifact.encoded_values, [0.0, math.pi / 2, math.pi])
    assert np.isclose(np.linalg.norm(artifact.statevector_real), 1.0)
    assert artifact.resources.parameters == 3


def test_amplitude_pads_and_normalizes() -> None:
    artifact = encode([1.0, 2.0, 3.0], "amplitude")
    assert artifact.padding == 1
    assert artifact.resources.qubits == 2
    assert np.isclose(np.linalg.norm(artifact.statevector_real), 1.0)
    assert artifact.statevector_real[-1] == 0.0


def test_amplitude_rejects_zero_vector() -> None:
    with pytest.raises(ValueError, match="all-zero"):
        encode([0.0, 0.0], "amplitude")


@pytest.mark.parametrize(
    ("values", "kind"),
    [([1.0, 0.0], "basis"), ([-0.5, 0.25], "angle"), ([1.0, 2.0, 3.0], "amplitude")],
)
def test_qiskit_and_pennylane_adapters_agree(values: list[float], kind: str) -> None:
    evidence = cross_check(values, kind)  # type: ignore[arg-type]
    assert evidence.equivalent_magnitudes is True
