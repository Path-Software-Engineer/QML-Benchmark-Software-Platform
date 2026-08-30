from __future__ import annotations

import os
from typing import Any

import requests


class BenchmarkApiClient:
    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or os.getenv("API_BASE_URL", "http://127.0.0.1:8080")).rstrip("/")

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = requests.request(
            method,
            f"{self.base_url}{path}",
            timeout=180,
            **kwargs,
        )
        response.raise_for_status()
        return response.json()

    def capabilities(self) -> dict[str, Any]:
        return dict(self._request("GET", "/api/v1/capabilities"))

    def datasets(self) -> list[dict[str, Any]]:
        return list(self._request("GET", "/api/v1/datasets"))

    def snapshot(self, snapshot_id: str) -> dict[str, Any]:
        return dict(self._request("GET", f"/api/v1/datasets/snapshots/{snapshot_id}"))

    def encodings(self) -> list[dict[str, Any]]:
        return list(self._request("GET", "/api/v1/encodings"))

    def preview(self, snapshot_id: str, sample_id: str, encoding: str) -> dict[str, Any]:
        return dict(
            self._request(
                "POST",
                "/api/v1/encodings/previews",
                json={
                    "snapshot_id": snapshot_id,
                    "sample_id": sample_id,
                    "encoding": encoding,
                },
            )
        )

    def manifest(self, preview_id: str) -> dict[str, Any]:
        return dict(self._request("GET", f"/api/v1/encodings/previews/{preview_id}/manifest"))

    def benchmark(
        self,
        snapshot_id: str,
        seeds: list[int],
        vqc_iterations: int,
    ) -> dict[str, Any]:
        return dict(
            self._request(
                "POST",
                "/api/v1/benchmarks/reports",
                json={
                    "snapshot_id": snapshot_id,
                    "seeds": seeds,
                    "vqc_iterations": vqc_iterations,
                },
            )
        )

    def report_csv(self, report_id: str) -> str:
        response = requests.get(
            f"{self.base_url}/api/v1/benchmarks/reports/{report_id}/report.csv",
            timeout=30,
        )
        response.raise_for_status()
        return response.text

    def evidence_imports(self) -> list[dict[str, Any]]:
        return list(self._request("GET", "/api/v1/evidence/imports"))
