from __future__ import annotations

import hashlib
import json
import os
import urllib.request

API = os.getenv("API_URL", "http://127.0.0.1:8080")
DASHBOARD = os.getenv("DASHBOARD_URL", "http://127.0.0.1:8050")


def request(path: str, payload: dict[str, object] | None = None) -> object:
    data = json.dumps(payload).encode() if payload is not None else None
    method = "POST" if payload is not None else "GET"
    call = urllib.request.Request(
        f"{API}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(call, timeout=30) as response:
        return json.load(response)


def main() -> None:
    datasets = request("/api/v1/datasets")
    assert isinstance(datasets, list)
    snapshot_id = datasets[0]["snapshot_id"]
    snapshot = request(f"/api/v1/datasets/snapshots/{snapshot_id}")
    assert snapshot["preprocessing"]["fitted_on"] == "train"
    previews = []
    requests = {
        "basis": [1, 0, 1],
        "angle": None,
        "amplitude": None,
    }
    for encoding, values in requests.items():
        payload: dict[str, object] = {
            "snapshot_id": snapshot_id,
            "sample_id": "s001",
            "encoding": encoding,
        }
        if values is not None:
            payload["values"] = values
        preview = request("/api/v1/encodings/previews", payload)
        assert preview["adapters"]["equivalent_magnitudes"] is True
        previews.append(preview)

    manifest = request(f"/api/v1/encodings/previews/{previews[-1]['preview_id']}/manifest")
    canonical = json.dumps(manifest["evidence"], sort_keys=True, separators=(",", ":"))
    assert manifest["sha256"] == hashlib.sha256(canonical.encode()).hexdigest()

    with urllib.request.urlopen(DASHBOARD, timeout=30) as response:
        assert response.status == 200
    with urllib.request.urlopen(f"{DASHBOARD}/_dash-layout", timeout=30) as response:
        layout = response.read().decode()
        assert "QML Evidence & Kernel Benchmark Console" in layout
        assert "Responsible interpretation" in layout

    report = request(
        "/api/v1/benchmarks/reports",
        {
            "snapshot_id": snapshot_id,
            "seeds": [2409],
            "vqc_iterations": 1,
        },
    )
    assert len(report["kernel_matrices"]) == 4
    assert len(report["runs"]) == 4
    assert report["provenance"]["quantum_advantage_claimed"] is False
    assert all(matrix["symmetric"] for matrix in report["kernel_matrices"])
    persisted = request(f"/api/v1/benchmarks/reports/{report['report_id']}")
    assert persisted["config_hash"] == report["config_hash"]
    imports = request("/api/v1/evidence/imports")
    assert len(imports) == 2

    with urllib.request.urlopen(
        f"{API}/api/v1/benchmarks/reports/{report['report_id']}/report.csv",
        timeout=30,
    ) as response:
        assert "model_id,repetitions,metric" in response.read().decode()

    print(
        "OK - Sprint 2 cross-layer smoke passed: Sprint 1 encodings plus four kernels, "
        "paired model runs, PostgreSQL report persistence, sealed imports, CSV export "
        "and Dash comparison surface"
    )


if __name__ == "__main__":
    main()
