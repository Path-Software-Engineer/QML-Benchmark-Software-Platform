from __future__ import annotations

from typing import Any


def encoding_catalog() -> list[dict[str, Any]]:
    return [
        {
            "id": "basis",
            "name": "Basis encoding",
            "input_contract": "Binary values only",
            "qubits": "one per feature",
            "normalization": "none",
            "limitation": "Continuous data needs an explicit discretization policy.",
        },
        {
            "id": "angle",
            "name": "Angle encoding",
            "input_contract": "Finite values; clipped to [-1, 1]",
            "qubits": "one per feature",
            "normalization": "linear map to [0, pi]",
            "limitation": "Clipping can discard scale information.",
        },
        {
            "id": "amplitude",
            "name": "Amplitude encoding",
            "input_contract": "Finite non-zero vector",
            "qubits": "ceil(log2(features))",
            "normalization": "L2",
            "limitation": "State preparation cost can offset compact qubit usage.",
        },
    ]
