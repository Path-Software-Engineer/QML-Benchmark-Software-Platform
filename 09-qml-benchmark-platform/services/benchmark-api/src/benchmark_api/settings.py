from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_url: str | None
    dataset_csv: Path
    dataset_manifest: Path
    evidence_root: Path | None = None


def load_settings() -> Settings:
    root = Path(os.getenv("PROJECT_ROOT", Path.cwd()))
    return Settings(
        database_url=os.getenv("DATABASE_URL"),
        dataset_csv=Path(os.getenv("DATASET_CSV", root / "data/datasets/qml_encoding_demo_v1.csv")),
        dataset_manifest=Path(
            os.getenv(
                "DATASET_MANIFEST",
                root / "data/datasets/qml_encoding_demo_v1.manifest.json",
            )
        ),
        evidence_root=Path(os.getenv("EVIDENCE_ROOT", root / "data/evidence")),
    )
