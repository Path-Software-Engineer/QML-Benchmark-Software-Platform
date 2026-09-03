from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Protocol

import psycopg


class EvidenceRepository(Protocol):
    def save_snapshot(self, snapshot_id: str, payload: Mapping[str, Any]) -> None: ...

    def get_snapshot(self, snapshot_id: str) -> dict[str, Any] | None: ...

    def save_preview(self, preview_id: str, payload: Mapping[str, Any]) -> None: ...

    def get_preview(self, preview_id: str) -> dict[str, Any] | None: ...

    def save_report(self, report_id: str, payload: Mapping[str, Any]) -> None: ...

    def get_report(self, report_id: str) -> dict[str, Any] | None: ...

    def save_noise_report(self, report_id: str, payload: Mapping[str, Any]) -> None: ...

    def get_noise_report(self, report_id: str) -> dict[str, Any] | None: ...

    def save_import(self, import_id: str, payload: Mapping[str, Any]) -> None: ...

    def get_import(self, import_id: str) -> dict[str, Any] | None: ...

    def is_ready(self) -> bool: ...


class MemoryEvidenceRepository:
    def __init__(self) -> None:
        self.snapshots: dict[str, dict[str, Any]] = {}
        self.previews: dict[str, dict[str, Any]] = {}
        self.reports: dict[str, dict[str, Any]] = {}
        self.noise_reports: dict[str, dict[str, Any]] = {}
        self.imports: dict[str, dict[str, Any]] = {}

    def save_snapshot(self, snapshot_id: str, payload: Mapping[str, Any]) -> None:
        self.snapshots[snapshot_id] = dict(payload)

    def get_snapshot(self, snapshot_id: str) -> dict[str, Any] | None:
        return self.snapshots.get(snapshot_id)

    def save_preview(self, preview_id: str, payload: Mapping[str, Any]) -> None:
        self.previews[preview_id] = dict(payload)

    def get_preview(self, preview_id: str) -> dict[str, Any] | None:
        return self.previews.get(preview_id)

    def save_report(self, report_id: str, payload: Mapping[str, Any]) -> None:
        self.reports[report_id] = dict(payload)

    def get_report(self, report_id: str) -> dict[str, Any] | None:
        return self.reports.get(report_id)

    def save_noise_report(self, report_id: str, payload: Mapping[str, Any]) -> None:
        self.noise_reports[report_id] = dict(payload)

    def get_noise_report(self, report_id: str) -> dict[str, Any] | None:
        return self.noise_reports.get(report_id)

    def save_import(self, import_id: str, payload: Mapping[str, Any]) -> None:
        self.imports[import_id] = dict(payload)

    def get_import(self, import_id: str) -> dict[str, Any] | None:
        return self.imports.get(import_id)

    def is_ready(self) -> bool:
        return True


class PostgresEvidenceRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def _execute(self, statement: str, parameters: tuple[object, ...]) -> None:
        with psycopg.connect(self.database_url) as connection, connection.cursor() as cursor:
            cursor.execute(statement, parameters)

    def _get(self, statement: str, identifier: str) -> dict[str, Any] | None:
        with psycopg.connect(self.database_url) as connection, connection.cursor() as cursor:
            cursor.execute(statement, (identifier,))
            row = cursor.fetchone()
            if row is None:
                return None
            payload = row[0]
            return dict(payload) if isinstance(payload, Mapping) else json.loads(str(payload))

    def save_snapshot(self, snapshot_id: str, payload: Mapping[str, Any]) -> None:
        self._execute(
            """
            INSERT INTO dataset_snapshots (snapshot_id, payload)
            VALUES (%s, %s::jsonb)
            ON CONFLICT (snapshot_id) DO UPDATE SET payload = EXCLUDED.payload
            """,
            (snapshot_id, json.dumps(payload)),
        )

    def get_snapshot(self, snapshot_id: str) -> dict[str, Any] | None:
        return self._get(
            "SELECT payload FROM dataset_snapshots WHERE snapshot_id = %s", snapshot_id
        )

    def save_preview(self, preview_id: str, payload: Mapping[str, Any]) -> None:
        self._execute(
            """
            INSERT INTO encoding_previews (preview_id, snapshot_id, encoding, payload)
            VALUES (%s, %s, %s, %s::jsonb)
            ON CONFLICT (preview_id) DO UPDATE SET payload = EXCLUDED.payload
            """,
            (
                preview_id,
                str(payload["snapshot_id"]),
                str(payload["artifact"]["encoding"]),
                json.dumps(payload),
            ),
        )

    def get_preview(self, preview_id: str) -> dict[str, Any] | None:
        return self._get("SELECT payload FROM encoding_previews WHERE preview_id = %s", preview_id)

    def save_report(self, report_id: str, payload: Mapping[str, Any]) -> None:
        self._execute(
            """
            INSERT INTO benchmark_reports (report_id, plan_id, snapshot_id, payload)
            VALUES (%s, %s, %s, %s::jsonb)
            ON CONFLICT (report_id) DO UPDATE SET payload = EXCLUDED.payload
            """,
            (
                report_id,
                str(payload["plan_id"]),
                str(payload["snapshot_id"]),
                json.dumps(payload),
            ),
        )

    def get_report(self, report_id: str) -> dict[str, Any] | None:
        return self._get("SELECT payload FROM benchmark_reports WHERE report_id = %s", report_id)

    def save_noise_report(self, report_id: str, payload: Mapping[str, Any]) -> None:
        self._execute(
            """
            INSERT INTO noise_reports (report_id, comparison_id, snapshot_id, payload)
            VALUES (%s, %s, %s, %s::jsonb)
            ON CONFLICT (report_id) DO UPDATE SET payload = EXCLUDED.payload
            """,
            (
                report_id,
                str(payload["comparison_id"]),
                str(payload["snapshot_id"]),
                json.dumps(payload),
            ),
        )

    def get_noise_report(self, report_id: str) -> dict[str, Any] | None:
        return self._get("SELECT payload FROM noise_reports WHERE report_id = %s", report_id)

    def save_import(self, import_id: str, payload: Mapping[str, Any]) -> None:
        self._execute(
            """
            INSERT INTO evidence_imports (import_id, source_project, bundle_sha256, payload)
            VALUES (%s, %s, %s, %s::jsonb)
            ON CONFLICT (import_id) DO UPDATE SET payload = EXCLUDED.payload
            """,
            (
                import_id,
                str(payload["source_project"]),
                str(payload["bundle_sha256"]),
                json.dumps(payload),
            ),
        )

    def get_import(self, import_id: str) -> dict[str, Any] | None:
        return self._get("SELECT payload FROM evidence_imports WHERE import_id = %s", import_id)

    def is_ready(self) -> bool:
        try:
            with psycopg.connect(self.database_url) as connection, connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return cursor.fetchone() == (1,)
        except psycopg.Error:
            return False
