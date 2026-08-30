from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).parents[1]
TEXT_SUFFIXES = {
    ".css",
    ".csv",
    ".dockerignore",
    ".example",
    ".gitignore",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".sql",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
EXCLUDED_PARTS = {".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tmp", ".venv"}
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)(?:password|token|secret)\s*[:=]\s*['\"][^${][^'\"]{10,}['\"]"),
]


def main() -> None:
    checked = 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or EXCLUDED_PARTS.intersection(path.parts):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {
            ".dockerignore",
            ".gitignore",
        }:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise SystemExit(f"non UTF-8 text file: {path.relative_to(ROOT)}") from error
        for number, line in enumerate(text.splitlines(), start=1):
            if line != line.rstrip():
                raise SystemExit(f"trailing whitespace: {path.relative_to(ROOT)}:{number}")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                raise SystemExit(f"possible committed credential: {path.relative_to(ROOT)}")
        checked += 1
    print(f"OK - repository hygiene passed for {checked} UTF-8 text files")


if __name__ == "__main__":
    main()
