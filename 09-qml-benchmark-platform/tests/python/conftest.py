from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT / "services/qml-core/src"))
sys.path.insert(0, str(ROOT / "services/benchmark-api/src"))
sys.path.insert(0, str(ROOT / "apps/dashboard"))
