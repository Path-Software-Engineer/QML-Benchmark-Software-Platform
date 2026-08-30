from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import asdict, replace
from datetime import UTC, datetime
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

from benchmark_api.repository import (
    EvidenceRepository,
    MemoryEvidenceRepository,
    PostgresEvidenceRepository,
)
from benchmark_api.schemas import (
    BenchmarkRequest,
    EvidenceImportRequest,
    PreviewRequest,
    PreviewResponse,
    ValidationRequest,
)
from benchmark_api.settings import Settings, load_settings
from qml_core.adapters import cross_check
from qml_core.benchmark import run_benchmark
from qml_core.benchmark_models import EvaluationProtocol
from qml_core.catalog import encoding_catalog
from qml_core.datasets import PreparedDataset, prepare_dataset, select_sample
from qml_core.encodings import encode
from qml_core.evaluation import model_registry
from qml_core.evidence import validate_evidence_bundle
from qml_core.kernels import kernel_registry


def create_app(
    settings: Settings | None = None,
    repository: EvidenceRepository | None = None,
) -> FastAPI:
    resolved = settings or load_settings()
    prepared = prepare_dataset(resolved.dataset_csv, resolved.dataset_manifest)
    repo = repository or (
        PostgresEvidenceRepository(resolved.database_url)
        if resolved.database_url
        else MemoryEvidenceRepository()
    )
    repo.save_snapshot(prepared.snapshot.snapshot_id, prepared.snapshot.as_dict())
    import_ids: list[str] = []
    if resolved.evidence_root and resolved.evidence_root.is_dir():
        for path in sorted(resolved.evidence_root.glob("*.pointer.json")):
            bundle = json.loads(path.read_text(encoding="utf-8"))
            result = validate_evidence_bundle(bundle)
            repo.save_import(str(result["import_id"]), result)
            import_ids.append(str(result["import_id"]))

    application = FastAPI(
        title="QML Benchmark Platform API",
        version="0.2.0",
        description=(
            "Executed encoding and paired kernel/model benchmark evidence. "
            "This release makes no quantum-advantage claim."
        ),
    )
    application.state.settings = resolved
    application.state.prepared = prepared
    application.state.repository = repo
    application.state.import_ids = import_ids

    def get_repository(request: Request) -> EvidenceRepository:
        return request.app.state.repository

    def get_dataset(request: Request) -> PreparedDataset:
        return request.app.state.prepared

    @application.exception_handler(ValueError)
    async def value_error_handler(_: Request, error: ValueError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(error)})

    @application.get("/health/live", tags=["health"])
    def live() -> dict[str, str]:
        return {"status": "live"}

    @application.get("/health/ready", tags=["health"])
    def ready(current: EvidenceRepository = Depends(get_repository)) -> dict[str, str]:
        if not current.is_ready():
            raise HTTPException(status_code=503, detail="evidence repository is unavailable")
        return {"status": "ready"}

    @application.get("/api/v1/capabilities", tags=["catalog"])
    def capabilities() -> dict[str, Any]:
        return {
            "schema_version": "qml.capabilities.v1",
            "release": "sprint-2",
            "encodings": [item["id"] for item in encoding_catalog()],
            "execution": ["numpy-reference", "qiskit-statevector", "pennylane-default.qubit"],
            "quantum_hardware_required": False,
            "quantum_advantage_claim": False,
            "benchmark_models": [spec.model_id for spec in model_registry(EvaluationProtocol())],
            "kernel_specs": [spec.kernel_id for spec in kernel_registry()],
        }

    @application.get("/api/v1/encodings", tags=["catalog"])
    def encodings() -> list[dict[str, Any]]:
        return encoding_catalog()

    @application.get("/api/v1/datasets", tags=["datasets"])
    def datasets(current: PreparedDataset = Depends(get_dataset)) -> list[dict[str, Any]]:
        snapshot = current.snapshot
        return [
            {
                "dataset_id": snapshot.dataset_id,
                "version": snapshot.dataset_version,
                "snapshot_id": snapshot.snapshot_id,
                "rows": snapshot.row_count,
                "features": list(snapshot.feature_names),
                "source": snapshot.source,
                "license": snapshot.license,
            }
        ]

    @application.post("/api/v1/datasets/snapshots", tags=["datasets"])
    def create_snapshot(
        current: PreparedDataset = Depends(get_dataset),
        storage: EvidenceRepository = Depends(get_repository),
    ) -> dict[str, Any]:
        payload = current.snapshot.as_dict()
        storage.save_snapshot(current.snapshot.snapshot_id, payload)
        return payload

    @application.get("/api/v1/datasets/snapshots/{snapshot_id}", tags=["datasets"])
    def get_snapshot(
        snapshot_id: str,
        storage: EvidenceRepository = Depends(get_repository),
    ) -> dict[str, Any]:
        payload = storage.get_snapshot(snapshot_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="snapshot not found")
        return payload

    @application.post("/api/v1/encodings/validate", tags=["encodings"])
    def validate(request: ValidationRequest) -> dict[str, Any]:
        artifact = encode(request.values, request.encoding)
        return {"valid": True, "artifact": artifact.as_dict()}

    @application.post(
        "/api/v1/encodings/previews",
        response_model=PreviewResponse,
        tags=["encodings"],
    )
    def create_preview(
        request: PreviewRequest,
        current: PreparedDataset = Depends(get_dataset),
        storage: EvidenceRepository = Depends(get_repository),
    ) -> dict[str, Any]:
        if request.snapshot_id != current.snapshot.snapshot_id:
            raise HTTPException(status_code=404, detail="snapshot not found")
        selected = select_sample(current, request.sample_id)
        values = tuple(request.values) if request.values is not None else selected
        input_derivation = (
            "request override" if request.values is not None else "train-scaled sample"
        )
        if request.encoding == "basis" and request.values is None:
            values = tuple(float(value >= 0.0) for value in selected)
            input_derivation = "explicit threshold: train-scaled feature >= 0 maps to 1"
        artifact = encode(values, request.encoding)
        if request.encoding == "basis" and request.values is None:
            artifact = replace(
                artifact,
                warnings=(
                    "Basis input was derived with the visible threshold policy: "
                    "train-scaled feature >= 0 maps to 1.",
                ),
            )
        adapters = cross_check(values, request.encoding)
        identity = json.dumps(
            {
                "snapshot_id": request.snapshot_id,
                "sample_id": request.sample_id,
                "encoding": request.encoding,
                "values": values,
            },
            sort_keys=True,
        )
        preview_id = f"preview-{hashlib.sha256(identity.encode()).hexdigest()[:16]}"
        payload = {
            "schema_version": "qml.encoding-preview.v1",
            "preview_id": preview_id,
            "snapshot_id": request.snapshot_id,
            "sample_id": request.sample_id,
            "artifact": artifact.as_dict(),
            "adapters": asdict(adapters),
            "provenance": {
                "created_at": datetime.now(UTC).isoformat(),
                "dataset_sha256": current.snapshot.content_hash,
                "preprocessing_fitted_on": current.snapshot.preprocessing.fitted_on,
                "input_derivation": input_derivation,
                "deterministic": True,
            },
        }
        storage.save_preview(preview_id, payload)
        return payload

    @application.get("/api/v1/encodings/previews/{preview_id}", tags=["encodings"])
    def get_preview(
        preview_id: str,
        storage: EvidenceRepository = Depends(get_repository),
    ) -> dict[str, Any]:
        payload = storage.get_preview(preview_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="preview not found")
        return payload

    @application.get("/api/v1/encodings/previews/{preview_id}/manifest", tags=["exports"])
    def export_manifest(
        preview_id: str,
        storage: EvidenceRepository = Depends(get_repository),
    ) -> dict[str, Any]:
        payload = storage.get_preview(preview_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="preview not found")
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return {
            "schema_version": "qml.evidence-bundle.v1",
            "sha256": hashlib.sha256(canonical.encode()).hexdigest(),
            "evidence": payload,
        }

    @application.get("/api/v1/benchmarks/protocol", tags=["benchmarks"])
    def benchmark_protocol() -> dict[str, Any]:
        return EvaluationProtocol().as_dict()

    @application.get("/api/v1/benchmarks/kernels", tags=["benchmarks"])
    def benchmark_kernels() -> list[dict[str, Any]]:
        return [spec.as_dict() for spec in kernel_registry()]

    @application.get("/api/v1/benchmarks/models", tags=["benchmarks"])
    def benchmark_models() -> list[dict[str, Any]]:
        protocol = EvaluationProtocol()
        return [spec.as_dict() for spec in model_registry(protocol)]

    @application.post("/api/v1/benchmarks/reports", tags=["benchmarks"])
    def create_benchmark_report(
        request: BenchmarkRequest,
        current: PreparedDataset = Depends(get_dataset),
        storage: EvidenceRepository = Depends(get_repository),
    ) -> dict[str, Any]:
        if request.snapshot_id != current.snapshot.snapshot_id:
            raise HTTPException(status_code=404, detail="snapshot not found")
        protocol = EvaluationProtocol(
            seeds=tuple(request.seeds),
            repetitions=len(request.seeds),
            max_vqc_iterations=request.vqc_iterations,
        )
        report = run_benchmark(current, protocol)
        payload = report.as_dict()
        storage.save_report(report.report_id, payload)
        return payload

    @application.get("/api/v1/benchmarks/reports/{report_id}", tags=["benchmarks"])
    def get_benchmark_report(
        report_id: str,
        storage: EvidenceRepository = Depends(get_repository),
    ) -> dict[str, Any]:
        payload = storage.get_report(report_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="benchmark report not found")
        return payload

    @application.get(
        "/api/v1/benchmarks/reports/{report_id}/matrices/{matrix_id}",
        tags=["benchmarks"],
    )
    def get_kernel_matrix(
        report_id: str,
        matrix_id: str,
        storage: EvidenceRepository = Depends(get_repository),
    ) -> dict[str, Any]:
        payload = storage.get_report(report_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="benchmark report not found")
        for matrix in payload["kernel_matrices"]:
            if matrix["matrix_id"] == matrix_id:
                return dict(matrix)
        raise HTTPException(status_code=404, detail="kernel matrix not found")

    @application.get(
        "/api/v1/benchmarks/reports/{report_id}/report.csv",
        response_class=PlainTextResponse,
        tags=["exports"],
    )
    def export_benchmark_csv(
        report_id: str,
        storage: EvidenceRepository = Depends(get_repository),
    ) -> str:
        payload = storage.get_report(report_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="benchmark report not found")
        stream = io.StringIO()
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["model_id", "repetitions", "metric", "mean", "std", "minimum", "maximum"])
        for aggregate in payload["aggregates"]:
            for metric, summary in aggregate["metrics"].items():
                writer.writerow(
                    [
                        aggregate["model_id"],
                        aggregate["repetitions"],
                        metric,
                        summary["mean"],
                        summary["std"],
                        summary["minimum"],
                        summary["maximum"],
                    ]
                )
        return stream.getvalue()

    @application.get(
        "/api/v1/benchmarks/reports/{report_id}/report.html",
        response_class=HTMLResponse,
        tags=["exports"],
    )
    def export_benchmark_html(
        report_id: str,
        storage: EvidenceRepository = Depends(get_repository),
    ) -> str:
        payload = storage.get_report(report_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="benchmark report not found")
        rows = "".join(
            "<tr><td>{}</td><td>{:.3f}</td><td>{:.3f}</td></tr>".format(
                aggregate["model_id"],
                aggregate["metrics"]["f1"]["mean"],
                aggregate["metrics"]["f1"]["std"],
            )
            for aggregate in payload["aggregates"]
        )
        limitations = "".join(f"<li>{item}</li>" for item in payload["limitations"])
        return (
            "<!doctype html><html lang='en'><meta charset='utf-8'>"
            f"<title>{report_id}</title><h1>QML benchmark report</h1>"
            "<p>Local bounded comparison; no quantum-advantage claim.</p>"
            f"<table><tr><th>Model</th><th>Mean F1</th><th>Std</th></tr>{rows}</table>"
            f"<h2>Limitations</h2><ul>{limitations}</ul></html>"
        )

    @application.post("/api/v1/evidence/imports", tags=["evidence"])
    def import_evidence(
        body: EvidenceImportRequest,
        request: Request,
        storage: EvidenceRepository = Depends(get_repository),
    ) -> dict[str, Any]:
        result = validate_evidence_bundle(body.bundle)
        existing = storage.get_import(str(result["import_id"]))
        if existing is not None:
            return existing
        storage.save_import(str(result["import_id"]), result)
        request.app.state.import_ids.append(str(result["import_id"]))
        return result

    @application.get("/api/v1/evidence/imports", tags=["evidence"])
    def list_evidence_imports(
        request: Request,
        storage: EvidenceRepository = Depends(get_repository),
    ) -> list[dict[str, Any]]:
        return [
            payload
            for import_id in request.app.state.import_ids
            if (payload := storage.get_import(import_id)) is not None
        ]

    @application.get("/api/v1/evidence/imports/{import_id}", tags=["evidence"])
    def get_evidence_import(
        import_id: str,
        storage: EvidenceRepository = Depends(get_repository),
    ) -> dict[str, Any]:
        payload = storage.get_import(import_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="evidence import not found")
        return payload

    return application


app = create_app()
