from __future__ import annotations

import hashlib
import json

from fastapi.testclient import TestClient

from benchmark_api.app import create_app
from benchmark_api.repository import MemoryEvidenceRepository
from benchmark_api.settings import Settings
from tests.python.conftest import ROOT


def client() -> TestClient:
    settings = Settings(
        database_url=None,
        dataset_csv=ROOT / "data/datasets/qml_encoding_demo_v1.csv",
        dataset_manifest=ROOT / "data/datasets/qml_encoding_demo_v1.manifest.json",
        evidence_root=ROOT / "data/evidence",
    )
    return TestClient(create_app(settings, MemoryEvidenceRepository()))


def test_capabilities_are_honest_and_hardware_independent() -> None:
    payload = client().get("/api/v1/capabilities").json()
    assert payload["quantum_hardware_required"] is False
    assert payload["quantum_advantage_claim"] is False
    assert payload["encodings"] == ["basis", "angle", "amplitude"]


def test_snapshot_exposes_train_only_preprocessing_and_disjoint_ids() -> None:
    current = client()
    snapshot_id = current.get("/api/v1/datasets").json()[0]["snapshot_id"]
    snapshot = current.get(f"/api/v1/datasets/snapshots/{snapshot_id}").json()
    assert snapshot["preprocessing"]["fitted_on"] == "train"
    groups = [set(snapshot["split"][key]) for key in ("train_ids", "validation_ids", "test_ids")]
    assert not groups[0] & groups[1]
    assert not groups[0] & groups[2]
    assert not groups[1] & groups[2]


def test_preview_is_executed_persisted_and_exported_with_digest() -> None:
    current = client()
    snapshot_id = current.get("/api/v1/datasets").json()[0]["snapshot_id"]
    response = current.post(
        "/api/v1/encodings/previews",
        json={"snapshot_id": snapshot_id, "sample_id": "s001", "encoding": "angle"},
    )
    assert response.status_code == 200
    preview = response.json()
    assert preview["adapters"]["equivalent_magnitudes"] is True
    assert preview["artifact"]["resources"]["qubits"] == 3
    assert current.get(f"/api/v1/encodings/previews/{preview['preview_id']}").status_code == 200
    bundle = current.get(f"/api/v1/encodings/previews/{preview['preview_id']}/manifest").json()
    canonical = json.dumps(bundle["evidence"], sort_keys=True, separators=(",", ":"))
    assert bundle["sha256"] == hashlib.sha256(canonical.encode()).hexdigest()


def test_invalid_encoding_contract_returns_422() -> None:
    response = client().post(
        "/api/v1/encodings/validate",
        json={"encoding": "basis", "values": [0.0, 0.2]},
    )
    assert response.status_code == 422
    assert "binary" in response.json()["detail"]


def test_benchmark_report_is_persisted_and_exported_in_three_formats() -> None:
    current = client()
    snapshot_id = current.get("/api/v1/datasets").json()[0]["snapshot_id"]
    response = current.post(
        "/api/v1/benchmarks/reports",
        json={"snapshot_id": snapshot_id, "seeds": [2409], "vqc_iterations": 1},
    )
    assert response.status_code == 200
    report = response.json()
    assert len(report["kernel_matrices"]) == 4
    assert len(report["runs"]) == 4
    assert report["provenance"]["quantum_advantage_claimed"] is False
    report_id = report["report_id"]
    assert current.get(f"/api/v1/benchmarks/reports/{report_id}").status_code == 200
    csv_export = current.get(f"/api/v1/benchmarks/reports/{report_id}/report.csv")
    assert csv_export.status_code == 200
    assert "model_id,repetitions,metric" in csv_export.text
    html_export = current.get(f"/api/v1/benchmarks/reports/{report_id}/report.html")
    assert html_export.status_code == 200
    assert "no quantum-advantage claim" in html_export.text


def test_sealed_p50_and_p51_evidence_is_preloaded_idempotently() -> None:
    current = client()
    imports = current.get("/api/v1/evidence/imports").json()
    assert len(imports) == 2
    assert {item["status"] for item in imports} == {"accepted"}
    bundle = json.loads(
        (ROOT / "data/evidence/p50-kernel-benchmark.pointer.json").read_text(encoding="utf-8")
    )
    first = current.post("/api/v1/evidence/imports", json={"bundle": bundle}).json()
    second = current.post("/api/v1/evidence/imports", json={"bundle": bundle}).json()
    assert first == second
