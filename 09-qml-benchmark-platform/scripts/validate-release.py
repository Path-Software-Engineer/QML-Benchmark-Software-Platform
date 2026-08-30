from __future__ import annotations

import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).parents[1]


def require(path: str) -> Path:
    target = ROOT / path
    if not target.is_file():
        raise SystemExit(f"required release artifact is missing: {path}")
    return target


def main() -> None:
    required = [
        "data/datasets/qml_encoding_demo_v1.csv",
        "data/datasets/qml_encoding_demo_v1.manifest.json",
        "services/qml-core/src/qml_core/encodings.py",
        "services/qml-core/src/qml_core/adapters.py",
        "services/benchmark-api/src/benchmark_api/app.py",
        "apps/dashboard/qml_dashboard/app.py",
        "database/migrations/0001_sprint_01_encoding_evidence.sql",
        "contracts/schemas/dataset-snapshot.schema.json",
        "contracts/schemas/encoding-preview.schema.json",
        "contracts/schemas/evidence-bundle.schema.json",
        "contracts/schemas/evaluation-protocol.schema.json",
        "contracts/schemas/kernel-spec.schema.json",
        "contracts/schemas/model-spec.schema.json",
        "contracts/schemas/kernel-matrix.schema.json",
        "contracts/schemas/benchmark-report.schema.json",
        "contracts/schemas/external-evidence.schema.json",
        "contracts/openapi.json",
        "data/evidence/p50-kernel-benchmark.pointer.json",
        "data/evidence/p51-vqc-qsvm-comparison.pointer.json",
        "services/qml-core/src/qml_core/kernels.py",
        "services/qml-core/src/qml_core/evaluation.py",
        "services/qml-core/src/qml_core/benchmark.py",
        "services/qml-core/src/qml_core/evidence.py",
        "database/migrations/0002_sprint_02_kernel_benchmarks.sql",
        "docs/adr/0001-sprint-01-boundaries.md",
        "docs/adr/0002-sprint-02-comparison-protocol.md",
        "docs/sprints/sprint-01-evidence.md",
        "docs/sprints/sprint-02-evidence.md",
        "design-system/qml-benchmark-platform-sprint-2/MASTER.md",
        "docker-compose.yml",
    ]
    for item in required:
        require(item)

    for schema_path in (ROOT / "contracts/schemas").glob("*.schema.json"):
        Draft202012Validator.check_schema(json.loads(schema_path.read_text(encoding="utf-8")))

    evidence_schema = json.loads(
        require("contracts/schemas/external-evidence.schema.json").read_text(encoding="utf-8")
    )
    for pointer_path in (ROOT / "data/evidence").glob("*.pointer.json"):
        pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
        Draft202012Validator(evidence_schema).validate(pointer)
        if pointer["quantum_advantage_claimed"] or pointer["status"] != "verified":
            raise SystemExit(f"unacceptable external evidence pointer: {pointer_path.name}")

    openapi = json.loads(require("contracts/openapi.json").read_text(encoding="utf-8"))
    required_paths = {
        "/api/v1/benchmarks/protocol",
        "/api/v1/benchmarks/kernels",
        "/api/v1/benchmarks/models",
        "/api/v1/benchmarks/reports",
        "/api/v1/evidence/imports",
    }
    if openapi.get("openapi") != "3.1.0" or not required_paths.issubset(openapi["paths"]):
        raise SystemExit("OpenAPI 3.1 contract is incomplete")

    dashboard = require("apps/dashboard/qml_dashboard/app.py").read_text(encoding="utf-8")
    forbidden = ["psycopg", "qml_core", "pennylane", "qiskit"]
    for dependency in forbidden:
        if re.search(rf"(?:from|import)\s+{dependency}", dashboard):
            raise SystemExit(f"Dash boundary violation: direct dependency on {dependency}")

    migration = require("database/migrations/0001_sprint_01_encoding_evidence.sql").read_text(
        encoding="utf-8"
    )
    if "dataset_snapshots" not in migration or "encoding_previews" not in migration:
        raise SystemExit("Sprint 1 persistence tables are incomplete")
    sprint_two_migration = require(
        "database/migrations/0002_sprint_02_kernel_benchmarks.sql"
    ).read_text(encoding="utf-8")
    if (
        "benchmark_reports" not in sprint_two_migration
        or "evidence_imports" not in sprint_two_migration
    ):
        raise SystemExit("Sprint 2 persistence tables are incomplete")

    readme = require("README.md").read_text(encoding="utf-8")
    if "quantum advantage" not in readme.lower():
        raise SystemExit("README must state the quantum-advantage evidence boundary")

    print("OK - Sprint 2 contracts, boundaries and versioned assets are structurally complete")


if __name__ == "__main__":
    main()
