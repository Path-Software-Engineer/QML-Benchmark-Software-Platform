from __future__ import annotations

import hashlib
import json
import re
from typing import Any

ALLOWED_UPSTREAM_SCHEMAS = {
    "kernel-bench.final-bundle-manifest.v1",
    "quantum-arena.final-bundle-manifest.v1",
    "hybrid-opt.bundle-manifest.v1",
}
FORBIDDEN_KEYS = {"code", "notebook", "pickle", "plugin", "python", "qasm"}
KNOWN_EVIDENCE: dict[str, dict[str, Any]] = {
    "Path-AI-Engineer/50-quantum-kernel-benchmark": {
        "source_manifest_sha256": (
            "d2b19f60d6c51fec536c6ae414be34e4ec9ddb5d8ecd51c761bb4ff01919cbdb"
        ),
        "source_summary_sha256": (
            "12069310519791a94e8a84b327f9a55653ddb071c725c623270e09912060d938"
        ),
        "summary": {
            "dataset_count": 8,
            "kernel_count": 11,
            "validation_run_count": 80,
            "test_case_count": 32,
            "negative_results_preserved": True,
            "multiple_comparisons_disclosed": True,
        },
    },
    "Path-AI-Engineer/51-vqc-qsvm-comparison-suite": {
        "source_manifest_sha256": (
            "1539a588c94943d74aab4fe8b75eb912196c2518012f9cfa237a4cfbeb10fcdf"
        ),
        "source_summary_sha256": (
            "879770cfd5ef494bab1f85cc5e22ea191b6208fbb953fc1aaa60768a3af46080"
        ),
        "summary": {
            "dataset_count": 8,
            "primary_method_count": 5,
            "validation_run_count": 40,
            "test_case_count": 40,
            "failed_run_count": 0,
            "universal_winner_claimed": False,
        },
    },
    "Path-AI-Engineer/52-vqe-qaoa-advanced-optimization": {
        "source_manifest_sha256": (
            "473d57f2b890b472fc5149a49068ee3b243c206bdd30415c83dac603fe24e86b"
        ),
        "source_summary_sha256": (
            "262f89a9a06e0474ce34d630ff2ded8396601f6f66dc7681052189f41468ad0c"
        ),
        "summary": {
            "final_case_count": 30,
            "run_count": 150,
            "profile_study_count": 6,
            "trainability_study_count": 4,
            "failed_run_count": 0,
            "post_test_tuning": False,
        },
    },
}


def _reject_executable_content(value: Any) -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if str(key).lower() in FORBIDDEN_KEYS:
                raise ValueError(f"evidence bundles cannot contain executable field: {key}")
            _reject_executable_content(nested)
    elif isinstance(value, list):
        for nested in value:
            _reject_executable_content(nested)


def validate_evidence_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version",
        "source_project",
        "upstream_schema",
        "source_manifest_sha256",
        "source_summary_sha256",
        "status",
        "protocol_state",
        "hardware_jobs",
        "quantum_advantage_claimed",
        "summary",
    }
    if set(bundle) != required:
        difference = sorted(set(bundle) ^ required)
        raise ValueError(f"evidence bundle fields differ from the allowlist: {difference}")
    if bundle["schema_version"] != "qml.external-evidence.v1":
        raise ValueError("unsupported QML evidence bundle schema")
    if bundle["upstream_schema"] not in ALLOWED_UPSTREAM_SCHEMAS:
        raise ValueError("upstream evidence schema is not allowlisted")
    if bundle["status"] != "verified" or bundle["protocol_state"] != "sealed":
        raise ValueError("only verified evidence from a sealed protocol can be imported")
    if bundle["quantum_advantage_claimed"] is not False:
        raise ValueError("bundles asserting quantum advantage are outside the release scope")
    if not isinstance(bundle["hardware_jobs"], int) or bundle["hardware_jobs"] < 0:
        raise ValueError("hardware_jobs must be a non-negative integer")
    for field in ("source_manifest_sha256", "source_summary_sha256"):
        if not re.fullmatch(r"[a-f0-9]{64}", str(bundle[field])):
            raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    _reject_executable_content(bundle)
    known = KNOWN_EVIDENCE.get(str(bundle["source_project"]))
    if known is None:
        raise ValueError("source project is not in the reviewed evidence registry")
    for field in ("source_manifest_sha256", "source_summary_sha256", "summary"):
        if bundle[field] != known[field]:
            raise ValueError(f"reviewed evidence identity mismatch: {field}")
    canonical = json.dumps(bundle, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    return {
        "schema_version": "qml.evidence-import-result.v1",
        "import_id": f"import-{digest[:16]}",
        "bundle_sha256": digest,
        "source_project": bundle["source_project"],
        "source_manifest_sha256": bundle["source_manifest_sha256"],
        "source_summary_sha256": bundle["source_summary_sha256"],
        "status": "accepted",
        "idempotent": True,
        "summary": bundle["summary"],
    }
