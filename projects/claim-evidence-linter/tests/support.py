from __future__ import annotations

import copy
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = PROJECT_ROOT / "demo" / "synthetic_contract.json"
EVIDENCE_PATH = PROJECT_ROOT / "demo" / "synthetic_evidence.json"


def fixture_values():
    contract_bytes = CONTRACT_PATH.read_bytes()
    evidence_bytes = EVIDENCE_PATH.read_bytes()
    return (
        json.loads(contract_bytes),
        contract_bytes,
        json.loads(evidence_bytes),
        evidence_bytes,
    )


def mutable_fixtures():
    contract, contract_bytes, evidence, evidence_bytes = fixture_values()
    return copy.deepcopy(contract), contract_bytes, copy.deepcopy(evidence), evidence_bytes

