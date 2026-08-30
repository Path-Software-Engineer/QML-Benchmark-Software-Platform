CREATE TABLE IF NOT EXISTS benchmark_reports (
    report_id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL,
    snapshot_id TEXT NOT NULL REFERENCES dataset_snapshots(snapshot_id),
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS benchmark_reports_plan_idx ON benchmark_reports(plan_id);

CREATE TABLE IF NOT EXISTS evidence_imports (
    import_id TEXT PRIMARY KEY,
    source_project TEXT NOT NULL,
    bundle_sha256 TEXT NOT NULL UNIQUE,
    payload JSONB NOT NULL,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO schema_migrations (version)
VALUES ('0002_sprint_02_kernel_benchmarks')
ON CONFLICT (version) DO NOTHING;
