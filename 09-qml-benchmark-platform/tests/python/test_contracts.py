from __future__ import annotations

import json

from jsonschema import Draft202012Validator

from tests.python.conftest import ROOT


def test_json_schemas_are_valid_2020_12_contracts() -> None:
    schemas = ROOT / "contracts/schemas"
    for path in schemas.glob("*.schema.json"):
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))


def test_external_evidence_pointers_conform_to_the_versioned_contract() -> None:
    schema = json.loads(
        (ROOT / "contracts/schemas/external-evidence.schema.json").read_text(encoding="utf-8")
    )
    validator = Draft202012Validator(schema)
    for path in (ROOT / "data/evidence").glob("*.pointer.json"):
        validator.validate(json.loads(path.read_text(encoding="utf-8")))
