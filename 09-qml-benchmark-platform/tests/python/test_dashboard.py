from __future__ import annotations

from typing import Any

from qml_dashboard.app import create_dash_app


class StubClient:
    def datasets(self) -> list[dict[str, Any]]:
        return [{"dataset_id": "demo", "snapshot_id": "snapshot-1"}]

    def encodings(self) -> list[dict[str, Any]]:
        return [{"id": "angle", "name": "Angle encoding"}]

    def snapshot(self, _: str) -> dict[str, Any]:
        return {"split": {"train_ids": ["s1"], "validation_ids": ["s2"], "test_ids": ["s3"]}}

    def preview(self, _: str, __: str, ___: str) -> dict[str, Any]:
        raise AssertionError("callbacks are not executed while constructing the layout")

    def manifest(self, _: str) -> dict[str, Any]:
        raise AssertionError("callbacks are not executed while constructing the layout")


def test_dashboard_is_http_client_only_and_has_accessible_evidence_regions() -> None:
    application = create_dash_app(StubClient())  # type: ignore[arg-type]
    layout = str(application.layout)
    assert "QML Benchmark & Limitations Console" in layout
    assert "Statevector evidence" in layout
    assert "Quantum Kernel Results Visualizer" in layout
    assert "Quality with variability" in layout
    assert "Kernel matrix heatmap" in layout
    assert "Responsible interpretation" in layout
    assert "Download evidence manifest" in layout
    assert "Quantum Noise Limitations Board" in layout
    assert "Mitigation paired by seed" in layout
    assert "Traceable limitation findings" in layout
    assert "Mitigation is not quantum error correction" in layout
