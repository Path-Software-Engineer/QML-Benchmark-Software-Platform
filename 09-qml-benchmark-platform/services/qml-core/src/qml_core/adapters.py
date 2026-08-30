from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import pennylane as qml
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector

from qml_core.encodings import encode
from qml_core.models import EncodingKind


@dataclass(frozen=True)
class AdapterEvidence:
    adapter: str
    statevector_real: tuple[float, ...]
    statevector_imaginary: tuple[float, ...]
    qubits: int
    depth: int
    operations: tuple[str, ...]


@dataclass(frozen=True)
class CrossCheckEvidence:
    equivalent_magnitudes: bool
    qiskit: AdapterEvidence
    pennylane: AdapterEvidence


def execute_qiskit(values: Sequence[float], kind: EncodingKind) -> AdapterEvidence:
    artifact = encode(values, kind)
    circuit = QuantumCircuit(artifact.resources.qubits)
    if kind == "basis":
        for gate in artifact.gates:
            circuit.x(artifact.resources.qubits - 1 - gate.wires[0])
    elif kind == "angle":
        for gate in artifact.gates:
            assert gate.parameter is not None
            circuit.ry(gate.parameter, artifact.resources.qubits - 1 - gate.wires[0])
    else:
        circuit.initialize(np.asarray(artifact.statevector_real), circuit.qubits)
    state = Statevector.from_instruction(circuit).data
    return AdapterEvidence(
        adapter="qiskit-statevector",
        statevector_real=tuple(float(value) for value in state.real),
        statevector_imaginary=tuple(float(value) for value in state.imag),
        qubits=circuit.num_qubits,
        depth=int(circuit.depth()),
        operations=tuple(str(item.operation.name) for item in circuit.data),
    )


def execute_pennylane(values: Sequence[float], kind: EncodingKind) -> AdapterEvidence:
    artifact = encode(values, kind)
    device = qml.device("default.qubit", wires=artifact.resources.qubits)

    @qml.qnode(device)
    def circuit() -> np.ndarray:
        if kind == "basis":
            qml.BasisState(np.asarray(artifact.encoded_values, dtype=int), wires=device.wires)
        elif kind == "angle":
            qml.AngleEmbedding(artifact.encoded_values, wires=device.wires, rotation="Y")
        else:
            qml.AmplitudeEmbedding(
                artifact.input_values,
                wires=device.wires,
                pad_with=0.0,
                normalize=True,
            )
        return qml.state()

    state = np.asarray(circuit())
    tape = circuit._tape
    return AdapterEvidence(
        adapter="pennylane-default.qubit",
        statevector_real=tuple(float(value) for value in state.real),
        statevector_imaginary=tuple(float(value) for value in state.imag),
        qubits=artifact.resources.qubits,
        depth=len(tape.operations),
        operations=tuple(operation.name for operation in tape.operations),
    )


def cross_check(values: Sequence[float], kind: EncodingKind) -> CrossCheckEvidence:
    qiskit = execute_qiskit(values, kind)
    pennylane = execute_pennylane(values, kind)
    equivalent = np.allclose(
        np.abs(qiskit.statevector_real),
        np.abs(pennylane.statevector_real),
        atol=1e-8,
    )
    return CrossCheckEvidence(
        equivalent_magnitudes=bool(equivalent),
        qiskit=qiskit,
        pennylane=pennylane,
    )
