CREATE TABLE IF NOT EXISTS noise_reports (
    report_id TEXT PRIMARY KEY,
    comparison_id TEXT NOT NULL,
    snapshot_id TEXT NOT NULL REFERENCES dataset_snapshots(snapshot_id),
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_noise_reports_comparison_id
    ON noise_reports (comparison_id);

CREATE INDEX IF NOT EXISTS idx_noise_reports_snapshot_id
    ON noise_reports (snapshot_id);

INSERT INTO schema_migrations (version)
VALUES ('0003_sprint_03_noise_limitations')
ON CONFLICT (version) DO NOTHING;
