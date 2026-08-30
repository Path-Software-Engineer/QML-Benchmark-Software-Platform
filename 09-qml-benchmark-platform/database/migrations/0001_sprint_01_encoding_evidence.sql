CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS dataset_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS encoding_previews (
    preview_id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL REFERENCES dataset_snapshots(snapshot_id),
    encoding TEXT NOT NULL CHECK (encoding IN ('basis', 'angle', 'amplitude')),
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO schema_migrations (version)
VALUES ('0001_sprint_01_encoding_evidence')
ON CONFLICT (version) DO NOTHING;
